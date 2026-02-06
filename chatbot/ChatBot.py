import json
from datetime import datetime
from openai import OpenAI # type: ignore

from database.QueryExecutor import QueryExecutor


# Schema summary provided to the model so it knows what tables/columns exist.
_DB_SCHEMA_DESCRIPTION = """\
The SQLite database tracks indoor locations. Tables:

1. zones (id, name, floor, department, polygon_coords, metadata, created_at)
2. entities (id, external_id, name, type['customer','employee','asset','device'], tags, first_seen, last_seen)
3. location_pings (id, entity_id FK->entities, zone_id FK->zones, timestamp, rssi, accuracy, source_device, raw_data)
4. zone_events (id, entity_id FK->entities, zone_id FK->zones, event_type['enter','exit','dwell'], start_time, end_time, duration_seconds, confidence)
"""

# OpenAI function-calling tool definition.
_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "execute_sql_query",
            "description": (
                "Execute a read-only SQL SELECT query against the database "
                "and return the results. Only SELECT statements are allowed. "
                "Here is the database schema:\n" + _DB_SCHEMA_DESCRIPTION
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "A SQL SELECT statement to execute.",
                    },
                },
                "required": ["query"],
            },
        },
    }
]

_SYSTEM_PROMPT = (
    "You are an operations assistant for an indoor location-tracking system. "
    "Your only purpose is to answer questions about the database. "
    "Answer the user's questions by querying the database when needed. "
    "Always prefer using the execute_sql_query tool to look up real data "
    "rather than guessing. Present results clearly and concisely."
    f"For queries involving time, use the current date and time {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} as the reference point. "
)


class ChatBot:
    """Conversational assistant backed by OpenAI with SQL function calling."""

    def __init__(self, query_executor: QueryExecutor, api_key: str) -> None:
        self._executor = query_executor
        self._client = OpenAI(api_key=api_key)
        self._messages: list[dict] = [
            {"role": "system", "content": _SYSTEM_PROMPT},
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
            tools=_TOOLS,
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
                tools=_TOOLS,
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
