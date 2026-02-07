"""API route definitions."""

import json

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import StreamingResponse

from api.auth import require_api_key
from api.rate_limit import get_remaining, get_reset_time, rate_limit, _get_limit
from api.schemas import (
    ChatRequest,
    ChatResponse,
    ConversationDetail,
    ConversationSummary,
    MessageSchema,
    RateLimitStatus,
)
from chatbot.ChatBot import ChatBot

router = APIRouter()


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------


@router.get("/health")
async def health_check():
    """Basic liveness probe -- no auth required."""
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _bot_dependency(request: Request) -> ChatBot:
    """Retrieve the shared ChatBot instance from app state."""
    return request.app.state.bot


# ---------------------------------------------------------------------------
# Conversation CRUD
# ---------------------------------------------------------------------------


@router.post(
    "/conversations",
    response_model=ConversationSummary,
    status_code=status.HTTP_201_CREATED,
)
async def create_conversation(
    api_key: str = Depends(require_api_key),
    bot: ChatBot = Depends(_bot_dependency),
):
    """Create a new conversation."""
    conversation = bot.create_conversation()
    return ConversationSummary(
        id=conversation.id,
        created_at=conversation.created_at.isoformat(),
        last_message=conversation.last_message.isoformat(),
    )


@router.get("/conversations", response_model=list[ConversationSummary])
async def list_conversations(
    api_key: str = Depends(require_api_key),
    bot: ChatBot = Depends(_bot_dependency),
):
    """List all active conversations."""
    return [
        ConversationSummary(
            id=c.id,
            created_at=c.created_at.isoformat(),
            last_message=c.last_message.isoformat(),
        )
        for c in bot._conversations.values()
    ]


@router.get("/conversations/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(
    conversation_id: str,
    api_key: str = Depends(require_api_key),
    bot: ChatBot = Depends(_bot_dependency),
):
    """Get a conversation with its full message history."""
    conversation = bot._conversations.get(conversation_id)
    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )

    messages = [
        MessageSchema(
            role=m.role,
            content=m.content,
            timestamp=m.timestamp.isoformat(),
        )
        for m in conversation.messages
        if m.role != "system"
    ]

    return ConversationDetail(
        id=conversation.id,
        created_at=conversation.created_at.isoformat(),
        last_message=conversation.last_message.isoformat(),
        messages=messages,
    )


@router.delete(
    "/conversations/{conversation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_conversation(
    conversation_id: str,
    api_key: str = Depends(require_api_key),
    bot: ChatBot = Depends(_bot_dependency),
):
    """Delete a conversation."""
    if conversation_id not in bot._conversations:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )
    del bot._conversations[conversation_id]


# ---------------------------------------------------------------------------
# Chat
# ---------------------------------------------------------------------------


@router.post(
    "/conversations/{conversation_id}/chat",
    response_model=ChatResponse,
)
async def chat(
    conversation_id: str,
    body: ChatRequest,
    response: Response,
    api_key: str = Depends(rate_limit),
    bot: ChatBot = Depends(_bot_dependency),
):
    """Send a message and receive the assistant's reply.

    This endpoint is rate-limited.
    """
    if conversation_id not in bot._conversations:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )

    conv_id, reply = bot.process_message(
        body.message,
        conversation_id=conversation_id,
    )

    remaining = get_remaining(api_key)
    limit = _get_limit()
    reset = get_reset_time(api_key)

    response.headers["X-RateLimit-Limit"] = str(limit)
    response.headers["X-RateLimit-Remaining"] = str(remaining)
    response.headers["X-RateLimit-Reset"] = reset

    return ChatResponse(
        conversation_id=conv_id,
        response=reply,
        remaining_requests=remaining,
    )


@router.post("/conversations/{conversation_id}/chat/stream")
async def chat_stream(
    conversation_id: str,
    body: ChatRequest,
    api_key: str = Depends(rate_limit),
    bot: ChatBot = Depends(_bot_dependency),
):
    """Send a message and stream the assistant's reply as Server-Sent Events.

    Each SSE event has an ``event`` field (status, tool_call, tool_result,
    token, done, error) and a JSON ``data`` payload.  This endpoint is
    rate-limited.
    """
    if conversation_id not in bot._conversations:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )

    def _event_generator():
        try:
            for event in bot.process_message_stream(
                body.message, conversation_id=conversation_id
            ):
                yield f"event: {event['type']}\ndata: {json.dumps(event)}\n\n"
        except Exception as exc:  # noqa: BLE001
            error_event = {"type": "error", "message": str(exc)}
            yield f"event: error\ndata: {json.dumps(error_event)}\n\n"

    return StreamingResponse(
        _event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


# ---------------------------------------------------------------------------
# Rate-limit status
# ---------------------------------------------------------------------------


@router.get("/rate-limit", response_model=RateLimitStatus)
async def get_rate_limit_status(
    api_key: str = Depends(require_api_key),
):
    """Return the current rate-limit status for the calling API key."""
    return RateLimitStatus(
        limit=_get_limit(),
        remaining=get_remaining(api_key),
        reset=get_reset_time(api_key),
    )
