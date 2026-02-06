"""API key authentication dependency."""

import os

from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader

_api_key_header = APIKeyHeader(name="Authorization")


def _get_valid_keys() -> set[str]:
    """Return the set of accepted API keys from the environment."""
    raw = os.environ.get("API_KEYS", "")
    return {k.strip() for k in raw.split(",") if k.strip()}


async def require_api_key(
    authorization: str = Depends(_api_key_header),
) -> str:
    """Validate the ``Authorization: Bearer <key>`` header.

    Returns:
        The validated API key string (used as the caller identity for
        rate limiting).

    Raises:
        HTTPException 401 if the key is missing or invalid.
    """
    # Accept "Bearer <key>" or a bare key
    token = authorization.removeprefix("Bearer ").strip()

    valid_keys = _get_valid_keys()
    if not valid_keys:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server has no API keys configured",
        )

    if token not in valid_keys:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )

    return token
