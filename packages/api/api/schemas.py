"""Pydantic request/response models for the API."""

from pydantic import BaseModel


class ChatRequest(BaseModel):
    """Body for the chat endpoint."""

    message: str


class ChatResponse(BaseModel):
    """Response from the chat endpoint."""

    conversation_id: str
    response: str
    remaining_requests: int


class MessageSchema(BaseModel):
    """A single message within a conversation."""

    role: str
    content: str | None
    timestamp: str


class ConversationSummary(BaseModel):
    """Lightweight representation of a conversation."""

    id: str
    created_at: str
    last_message: str


class ConversationDetail(BaseModel):
    """Full conversation including its messages."""

    id: str
    created_at: str
    last_message: str
    messages: list[MessageSchema]


class RateLimitStatus(BaseModel):
    """Current rate-limit status for the calling API key."""

    limit: int
    remaining: int
    reset: str
