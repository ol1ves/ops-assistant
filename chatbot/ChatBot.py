import json

from openai import OpenAI  # type: ignore

from chatbot.system_prompt import SYSTEM_PROMPT
from chatbot.tools import TOOLS
from database.QueryExecutor import QueryExecutor


class ChatBot:
    """Conversational assistant backed by OpenAI with SQL function calling."""

    def __init__(self, query_executor: QueryExecutor, api_key: str) -> None:
        self._executor = query_executor
        self._client = OpenAI(api_key=api_key)
        self._messages: list[dict] = [
            {"role": "system", "content": SYSTEM_PROMPT},
        ]

    def chat(self, user_message: str) -> str:
        """Send a user message and return the assistant's response.

        If the model requests tool calls, they are executed via the
        QueryExecutor and the results are fed back for a follow-up response.

        Args:
            user_message: The message from the user.

        Returns:
            The assistant's final text reply.
        """
        self._messages.append({"role": "user", "content": user_message})

        response = self._client.chat.completions.create(
            model="gpt-4o-mini",
            messages=self._messages,
            tools=TOOLS,
        )

        message = response.choices[0].message
        self._messages.append(message)

        # Handle tool calls (may require multiple rounds)
        while message.tool_calls:
            for tool_call in message.tool_calls:
                result = self._handle_tool_call(tool_call)
                self._messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result,
                    }
                )

            response = self._client.chat.completions.create(
                model="gpt-4o-mini",
                messages=self._messages,
                tools=TOOLS,
            )
            message = response.choices[0].message
            self._messages.append(message)

        return message.content or ""

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
