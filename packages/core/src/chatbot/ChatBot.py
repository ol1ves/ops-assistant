"""Core chatbot module that orchestrates OpenAI completions with SQL tool calls."""

import json
from collections.abc import Callable, Generator

from openai import OpenAI  # type: ignore

from chatbot.models import Conversation, Message, ToolCallRecord
from chatbot.prompts import (
    get_interpretation_prompt,
    get_reasoning_prompt,
    get_system_prompt,
)
from chatbot.tools import TOOLS
from database.QueryExecutor import QueryExecutor


class ChatBot:
    """Conversational assistant backed by OpenAI with SQL function calling."""

    def __init__(self, query_executor: QueryExecutor, api_key: str) -> None:
        """Initialize the chatbot with a query executor and OpenAI API key.

        Args:
            query_executor: Validated, read-only SQL executor for database access.
            api_key: OpenAI API key used to authenticate completion requests.
        """
        self._executor = query_executor
        self._client = OpenAI(api_key=api_key)
        self._conversations: dict[str, Conversation] = {}

    def create_conversation(self) -> Conversation:
        """Create a new conversation seeded with the system prompt.

        Returns:
            The newly created Conversation.
        """
        conversation = Conversation()
        conversation.add_message(
            Message(role="system", content=get_system_prompt(), type="system")
        )
        self._conversations[conversation.id] = conversation
        return conversation

    @staticmethod
    def _refresh_system_prompt(conversation: Conversation) -> None:
        """Update the system message with a freshly-timestamped prompt.

        Must be called before every API request so the model always has
        the current date/time for resolving relative time references.
        """
        if conversation.messages and conversation.messages[0].role == "system":
            conversation.messages[0].content = get_system_prompt()

    def _process_message_events(
        self,
        user_message: str,
        conversation_id: str | None = None,
    ) -> Generator[dict, None, None]:
        """Yield processing events for a user message (internal implementation)."""
        # Resolve or create the conversation
        conversation = self._conversations.get(conversation_id or "")
        if conversation is None:
            conversation = self.create_conversation()

        # Refresh the system prompt so the model sees the current timestamp
        self._refresh_system_prompt(conversation)

        conversation.add_message(
            Message(role="user", content=user_message, type="request")
        )
        api_messages = [m.to_api_dict() for m in conversation.messages]
        api_messages[0]["content"] = (
            get_system_prompt() + "\n\n" + get_reasoning_prompt()
        )

        while True:
            yield {"type": "status", "status": "thinking"}

            stream = self._client.chat.completions.create(
                model="gpt-4o-mini",
                messages=api_messages,
                tools=TOOLS,
                stream=True,
            )

            content_parts: list[str] = []
            tool_calls_acc: dict[int, dict] = {}

            for chunk in stream:
                choice = chunk.choices[0]
                delta = choice.delta

                if delta.content:
                    content_parts.append(delta.content)
                    yield {"type": "token", "token": delta.content}

                if delta.tool_calls:
                    for tc_delta in delta.tool_calls:
                        idx = tc_delta.index
                        if idx not in tool_calls_acc:
                            tool_calls_acc[idx] = {
                                "id": "",
                                "name": "",
                                "arguments": "",
                            }
                        if tc_delta.id:
                            tool_calls_acc[idx]["id"] = tc_delta.id
                        if tc_delta.function:
                            if tc_delta.function.name:
                                tool_calls_acc[idx]["name"] = tc_delta.function.name
                            if tc_delta.function.arguments:
                                tool_calls_acc[idx]["arguments"] += (
                                    tc_delta.function.arguments
                                )

            full_content = "".join(content_parts) or None

            # No tool calls – single final answer (output)
            if not tool_calls_acc:
                assistant_msg = Message(
                    role="assistant", content=full_content, type="output"
                )
                conversation.add_message(assistant_msg)
                yield {
                    "type": "done",
                    "conversation_id": conversation.id,
                    "response": full_content or "",
                }
                return

            # Tool calls – add reasoning message, execute tools
            raw_tool_calls = []
            for idx in sorted(tool_calls_acc):
                tc = tool_calls_acc[idx]
                raw_tool_calls.append(
                    {
                        "id": tc["id"],
                        "type": "function",
                        "function": {
                            "name": tc["name"],
                            "arguments": tc["arguments"],
                        },
                    }
                )

            assistant_msg = Message(
                role="assistant",
                content=full_content,
                type="reasoning",
                _raw_tool_calls=raw_tool_calls,
            )
            conversation.add_message(assistant_msg)

            tool_call_records: list[ToolCallRecord] = []
            any_failed = False
            for raw_tc in raw_tool_calls:
                args = json.loads(raw_tc["function"]["arguments"])
                sql_query = args.get("query", "")

                yield {"type": "tool_call", "query": sql_query}

                result = self._execute_tool(
                    raw_tc["function"]["name"],
                    raw_tc["function"]["arguments"],
                )

                success = "error" not in json.loads(result)
                if not success:
                    any_failed = True
                yield {
                    "type": "tool_result",
                    "query": sql_query,
                    "success": success,
                }

                tool_call_records.append(
                    ToolCallRecord(query=sql_query, response=result)
                )
                conversation.add_message(
                    Message(
                        role="tool",
                        content=result,
                        tool_call_id=raw_tc["id"],
                        type="tool",
                    )
                )

            assistant_msg.tool_calls = tool_call_records

            # If any tool call failed, return to reasoning so the model can retry
            if any_failed:
                api_messages = [m.to_api_dict() for m in conversation.messages]
                api_messages[0]["content"] = (
                    "One or more tool calls failed. Please retry."
                )
                continue

            # All tool calls succeeded – proceed to interpretation phase
            break

        # Interpretation phase: system + interpretation prompt, then conversation
        api_messages = [m.to_api_dict() for m in conversation.messages]
        api_messages[0]["content"] = (
            get_system_prompt() + "\n\n" + get_interpretation_prompt()
        )

        yield {"type": "status", "status": "thinking"}

        stream = self._client.chat.completions.create(
            model="gpt-4o-mini",
            messages=api_messages,
            tools=TOOLS,
            stream=True,
        )

        content_parts = []
        for chunk in stream:
            choice = chunk.choices[0]
            delta = choice.delta
            if delta.content:
                content_parts.append(delta.content)
                yield {"type": "token", "token": delta.content}

        interpret_content = "".join(content_parts) or ""
        interpret_msg = Message(
            role="assistant", content=interpret_content, type="interpret"
        )
        conversation.add_message(interpret_msg)
        yield {
            "type": "done",
            "conversation_id": conversation.id,
            "response": interpret_content,
        }

    def process_message(
        self,
        user_message: str,
        conversation_id: str | None = None,
        on_tool_call: Callable[[str], None] | None = None,
    ) -> tuple[str, str]:
        """Process a user message within a conversation.

        If no conversation_id is provided (or it is not found), a new
        conversation is created automatically.

        Args:
            user_message: The message from the user.
            conversation_id: Optional existing conversation identifier.
            on_tool_call: Optional callback invoked with the SQL query string
                each time a tool call is executed.

        Returns:
            A tuple of (conversation_id, assistant_response_text).
        """
        for event in self._process_message_events(user_message, conversation_id):
            if event.get("type") == "tool_call" and on_tool_call:
                on_tool_call(event.get("query", ""))
            if event.get("type") == "done":
                return (
                    event["conversation_id"],
                    event.get("response", "") or "",
                )
        return ("", "")

    def process_message_stream(
        self,
        user_message: str,
        conversation_id: str | None = None,
    ) -> Generator[dict, None, None]:
        """Process a user message, yielding SSE-friendly event dicts.

        Yields events of the following types:
            - ``status``      – processing phase (e.g. "thinking")
            - ``tool_call``   – a SQL query is about to be executed
            - ``tool_result`` – the query finished (includes success flag)
            - ``token``       – a single content token from the model
            - ``done``        – final response with full text
            - ``error``       – something went wrong

        Args:
            user_message: The message from the user.
            conversation_id: Optional existing conversation identifier.

        Yields:
            Dicts that the API layer can serialise as SSE events.
        """
        yield from self._process_message_events(user_message, conversation_id)

    # ------------------------------------------------------------------
    # Tool execution helpers
    # ------------------------------------------------------------------

    def _execute_tool(self, function_name: str, arguments: str) -> str:
        """Execute a tool by function name and raw JSON arguments string."""
        if function_name != "execute_sql_query":
            return json.dumps({"error": f"Unknown tool: {function_name}"})

        try:
            args = json.loads(arguments)
            rows = self._executor.execute_safe_query(args["query"])
            return json.dumps({"results": [list(row) for row in rows]})
        except (ValueError, RuntimeError) as e:
            return json.dumps({"error": str(e)})

    def _handle_tool_call(self, tool_call) -> str:
        """Execute a single tool call and return the result as a string."""
        return self._execute_tool(
            tool_call.function.name, tool_call.function.arguments
        )
