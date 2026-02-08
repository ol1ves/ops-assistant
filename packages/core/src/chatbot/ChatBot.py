"""Core chatbot module that orchestrates OpenAI completions with SQL tool calls."""

import json
from collections.abc import Callable, Generator

import tiktoken # type: ignore
from openai import BadRequestError, OpenAI  # type: ignore

from chatbot.models import Conversation, Message, ToolCallRecord
from chatbot.prompts import (
    get_interpretation_prompt,
    get_reasoning_prompt,
    get_system_prompt,
)
from chatbot.tools import TOOLS
from database.QueryExecutor import QueryExecutor

# Reserve space for tools (~283) and model response. gpt-4o-mini context is 128k.
MAX_CONTEXT_TOKENS = 128_000
MAX_REQUEST_TOKENS = MAX_CONTEXT_TOKENS - 5_000

_CONTEXT_LENGTH_MSG = (
    "Conversation is too long. Please start a new conversation."
)


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

    @staticmethod
    def _count_tokens_for_messages(encoding: tiktoken.Encoding, messages: list[dict]) -> int:
        """Return estimated token count for a list of API-style message dicts."""
        # Per cookbook: 3 tokens per message overhead, plus content; gpt-4o-mini uses 3.
        tokens_per_message = 3
        num_tokens = 0
        for msg in messages:
            num_tokens += tokens_per_message
            for key, value in msg.items():
                if value is None:
                    continue
                if isinstance(value, str):
                    num_tokens += len(encoding.encode(value))
                elif key == "tool_calls" and isinstance(value, list):
                    num_tokens += len(encoding.encode(json.dumps(value)))
                else:
                    num_tokens += len(encoding.encode(str(value)))
        num_tokens += 3  # every reply primed with <|start|>assistant<|message|>
        return num_tokens

    def _build_api_messages(
        self,
        conversation: Conversation,
        system_content: str,
        max_tokens: int = MAX_REQUEST_TOKENS,
    ) -> list[dict]:
        """Build API message list with system first and as many recent turns as fit.

        Does not mutate conversation.messages. Truncates by dropping oldest turns
        so tool-call chains stay valid.
        """
        try:
            encoding = tiktoken.encoding_for_model("gpt-4o-mini")
        except KeyError:
            encoding = tiktoken.get_encoding("o200k_base")

        system_msg = {"role": "system", "content": system_content}

        # Split non-system messages into turns: each turn = user + following assistant/tool
        rest = conversation.messages[1:]
        turns: list[list[Message]] = []
        current_turn: list[Message] = []
        for m in rest:
            if m.role == "user":
                if current_turn:
                    turns.append(current_turn)
                current_turn = [m]
            else:
                current_turn.append(m)
        if current_turn:
            turns.append(current_turn)

        # Include as many full turns from the end as fit
        tail: list[Message] = []
        for turn in reversed(turns):
            candidate = list(turn) + tail
            msgs = [system_msg] + [x.to_api_dict() for x in candidate]
            if self._count_tokens_for_messages(encoding, msgs) <= max_tokens:
                tail = candidate
            else:
                break

        return [system_msg] + [m.to_api_dict() for m in tail]

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
        reasoning_system = (
            get_system_prompt() + "\n\n" + get_reasoning_prompt()
        )
        api_messages = self._build_api_messages(
            conversation, reasoning_system
        )

        last_reasoning_content: str = ""
        while True:
            yield {"type": "status", "status": "thinking"}

            try:
                stream = self._client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=api_messages,
                    tools=TOOLS,
                    stream=True,
                )
            except BadRequestError as e:
                if "context_length_exceeded" not in str(e):
                    raise
                api_messages = self._build_api_messages(
                    conversation, reasoning_system, max_tokens=12_000
                )
                try:
                    stream = self._client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=api_messages,
                        tools=TOOLS,
                        stream=True,
                    )
                except BadRequestError as e2:
                    if "context_length_exceeded" in str(e2):
                        raise RuntimeError(_CONTEXT_LENGTH_MSG) from e2
                    raise

            content_parts: list[str] = []
            tool_calls_acc: dict[int, dict] = {}

            for chunk in stream:
                choice = chunk.choices[0]
                delta = choice.delta

                if delta.content:
                    content_parts.append(delta.content)
                    # Stream reasoning to the dropdown only (not the main response).
                    yield {"type": "reasoning_token", "token": delta.content}

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

            # Always emit reasoning so the UI can show the step; use placeholder if model sent no text
            last_reasoning_content = (full_content or "").strip() or "(Planning step — no model text.)"
            yield {"type": "reasoning", "content": last_reasoning_content}

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
                    "result": result,
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
                api_messages = self._build_api_messages(
                    conversation, "One or more tool calls failed. Please retry."
                )
                continue

            # All tool calls succeeded – proceed to interpretation phase
            break

        # Interpretation phase: system + interpretation prompt, then conversation
        interpret_system = (
            get_system_prompt() + "\n\n" + get_interpretation_prompt()
        )
        api_messages = self._build_api_messages(
            conversation, interpret_system
        )
        yield {"type": "status", "status": "thinking"}

        try:
            stream = self._client.chat.completions.create(
                model="gpt-4o-mini",
                messages=api_messages,
                tools=TOOLS,
                stream=True,
            )
        except BadRequestError as e:
            if "context_length_exceeded" not in str(e):
                raise
            api_messages = self._build_api_messages(
                conversation, interpret_system, max_tokens=12_000
            )
            try:
                stream = self._client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=api_messages,
                    tools=TOOLS,
                    stream=True,
                )
            except BadRequestError as e2:
                if "context_length_exceeded" in str(e2):
                    raise RuntimeError(_CONTEXT_LENGTH_MSG) from e2
                raise

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
        # Send only the interpretation as the final response; reasoning stays in the reasoning UI
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
