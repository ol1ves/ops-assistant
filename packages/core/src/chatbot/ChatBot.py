"""Core chatbot module that orchestrates OpenAI completions with SQL tool calls."""

import json
from collections.abc import Callable

from openai import OpenAI  # type: ignore

from chatbot.models import Conversation, Message, ToolCallRecord
from chatbot.system_prompt import SYSTEM_PROMPT
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
        conversation.add_message(Message(role="system", content=SYSTEM_PROMPT))
        self._conversations[conversation.id] = conversation
        return conversation

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
        # Resolve or create the conversation
        conversation = self._conversations.get(conversation_id or "")
        if conversation is None:
            conversation = self.create_conversation()

        # Record the user message
        conversation.add_message(Message(role="user", content=user_message))

        # Build the API messages list and call the model
        api_messages = [m.to_api_dict() for m in conversation.messages]

        response = self._client.chat.completions.create(
            model="gpt-4o-mini",
            messages=api_messages,
            tools=TOOLS,
        )

        message = response.choices[0].message

        # Record the assistant message (may contain tool calls)
        assistant_msg = Message(
            role="assistant",
            content=message.content,
            _raw_tool_calls=(
                [tc.model_dump() for tc in message.tool_calls]
                if message.tool_calls
                else None
            ),
        )
        conversation.add_message(assistant_msg)

        # Handle tool calls (may require multiple rounds)
        while message.tool_calls:
            tool_call_records: list[ToolCallRecord] = []

            for tool_call in message.tool_calls:
                args = json.loads(tool_call.function.arguments)
                sql_query = args.get("query", "")

                if on_tool_call and sql_query:
                    on_tool_call(sql_query)

                result = self._handle_tool_call(tool_call)
                tool_call_records.append(
                    ToolCallRecord(query=sql_query, response=result)
                )

                conversation.add_message(
                    Message(
                        role="tool",
                        content=result,
                        tool_call_id=tool_call.id,
                    )
                )

            # Attach tool call records to the preceding assistant message
            assistant_msg.tool_calls = tool_call_records

            # Re-build API messages and request a follow-up
            api_messages = [m.to_api_dict() for m in conversation.messages]

            response = self._client.chat.completions.create(
                model="gpt-4o-mini",
                messages=api_messages,
                tools=TOOLS,
            )

            message = response.choices[0].message
            assistant_msg = Message(
                role="assistant",
                content=message.content,
                _raw_tool_calls=(
                    [tc.model_dump() for tc in message.tool_calls]
                    if message.tool_calls
                    else None
                ),
            )
            conversation.add_message(assistant_msg)

        return conversation.id, message.content or ""

    def _handle_tool_call(self, tool_call) -> str:
        """Execute a single tool call and return the result as a string."""
        if tool_call.function.name != "execute_sql_query":
            return json.dumps({"error": f"Unknown tool: {tool_call.function.name}"})

        try:
            args = json.loads(tool_call.function.arguments)
            rows = self._executor.execute_safe_query(args["query"])
            return json.dumps({"results": [list(row) for row in rows]})
        except (ValueError, RuntimeError) as e:
            return json.dumps({"error": str(e)})
