"""Per-API-key sliding-window rate limiter."""

import os
import time
from collections import defaultdict
from datetime import datetime, timezone

from fastapi import Depends, HTTPException, Request, status

from api.auth import require_api_key

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

WINDOW_SECONDS = 3600  # 1 hour


def _get_limit() -> int:
    return int(os.environ.get("RATE_LIMIT_PER_HOUR", "20"))


# ---------------------------------------------------------------------------
# In-memory storage: api_key -> list of request timestamps
# ---------------------------------------------------------------------------

_request_log: dict[str, list[float]] = defaultdict(list)


def _prune(api_key: str, now: float) -> None:
    """Remove timestamps older than the sliding window."""
    cutoff = now - WINDOW_SECONDS
    _request_log[api_key] = [
        ts for ts in _request_log[api_key] if ts > cutoff
    ]


# ---------------------------------------------------------------------------
# Public helpers (used by routes to query status without incrementing)
# ---------------------------------------------------------------------------


def get_remaining(api_key: str) -> int:
    """Return how many requests remain in the current window."""
    now = time.time()
    _prune(api_key, now)
    return max(0, _get_limit() - len(_request_log[api_key]))


def get_reset_time(api_key: str) -> str:
    """Return an ISO-8601 timestamp for when the oldest request expires."""
    timestamps = _request_log.get(api_key, [])
    if not timestamps:
        return datetime.now(timezone.utc).isoformat()
    oldest = min(timestamps)
    reset_at = oldest + WINDOW_SECONDS
    return datetime.fromtimestamp(reset_at, tz=timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------


async def rate_limit(
    request: Request,
    api_key: str = Depends(require_api_key),
) -> str:
    """Enforce the per-key rate limit.

    This dependency should be added to endpoints that consume tokens
    (i.e. the chat endpoint).  It records the request and raises 429
    if the caller has exhausted their allowance.

    Returns:
        The validated API key (pass-through from auth).
    """
    now = time.time()
    _prune(api_key, now)

    limit = _get_limit()

    if len(_request_log[api_key]) >= limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded",
            headers={
                "X-RateLimit-Limit": str(limit),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": get_reset_time(api_key),
            },
        )

    _request_log[api_key].append(now)
    return api_key
