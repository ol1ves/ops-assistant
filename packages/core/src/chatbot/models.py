"""Data models for chatbot messages and conversations."""

import uuid
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ToolCallRecord:
    """A record of a single tool call made during a conversation turn."""

    query: str
    response: str


@dataclass
class Message:
    """A single message within a conversation.

    Attributes:
        role: One of "system", "user", "assistant", or "tool".
        content: The text content of the message (may be None for
            assistant messages that only contain tool calls).
        type: Semantic type for display: "request", "reasoning", "interpret",
            "output", "system", or "tool". Defaults by role when not set.
        tool_calls: Records of SQL tool calls and their responses.
        tool_call_id: The tool_call_id for tool-role messages.
        timestamp: When the message was created.
    """

    role: str
    content: str | None = None
    type: str = ""
    tool_calls: list[ToolCallRecord] | None = None
    tool_call_id: str | None = None
    timestamp: datetime = field(default_factory=datetime.now)

    # Raw tool_calls objects from the OpenAI API response, stored so that
    # to_api_dict() can include them verbatim on assistant messages.
    _raw_tool_calls: list | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        """Set default type from role when type was not provided."""
        if not self.type and self.role == "user":
            object.__setattr__(self, "type", "request")
        elif not self.type and self.role == "system":
            object.__setattr__(self, "type", "system")
        elif not self.type and self.role == "tool":
            object.__setattr__(self, "type", "tool")
        elif not self.type and self.role == "assistant":
            object.__setattr__(self, "type", "output")

    def to_api_dict(self) -> dict:
        """Serialize this message into the dict format expected by the OpenAI API.

        Returns:
            A dictionary suitable for inclusion in the ``messages`` list of a
            chat completion request.
        """
        if self.role == "tool":
            return {
                "role": "tool",
                "tool_call_id": self.tool_call_id,
                "content": self.content or "",
            }

        result: dict = {"role": self.role}

        if self.content is not None:
            result["content"] = self.content

        if self._raw_tool_calls:
            result["tool_calls"] = self._raw_tool_calls

        return result


class Conversation:
    """An ordered sequence of messages with a unique identifier.

    Attributes:
        id: A unique hex string identifying this conversation.
        messages: The list of messages in chronological order.
        created_at: When the conversation was created.
        last_message: Timestamp of the most recently added message.
    """

    def __init__(self) -> None:
        self.id: str = uuid.uuid4().hex
        self.messages: list[Message] = []
        self.created_at: datetime = datetime.now()
        self.last_message: datetime = self.created_at

    def add_message(self, message: Message) -> None:
        """Append a message and update the last_message timestamp."""
        self.messages.append(message)
        self.last_message = message.timestamp
