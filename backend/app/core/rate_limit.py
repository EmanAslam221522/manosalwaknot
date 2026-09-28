from __future__ import annotations

from functools import lru_cache

from fastapi import Request
from redis import Redis

from app.core.config import get_settings
from app.core.errors import ApiError


@lru_cache
def get_redis() -> Redis[str]:
    return Redis.from_url(
        get_settings().redis_url,
        decode_responses=True,
        socket_connect_timeout=5,
        socket_timeout=5,
    )


def check_redis() -> bool:
    try:
        return bool(get_redis().ping())
    except Exception:
        return False


def enforce_rate_limit(
    request: Request,
    scope: str,
    limit: int,
    window_seconds: int,
    subject: str | None = None,
) -> None:
    client = request.client.host if request.client else "unknown"
    key = f"rate:{scope}:{subject or client}"
    try:
        redis = get_redis()
        count = redis.incr(key)
        if count == 1:
            redis.expire(key, window_seconds)
    except Exception as exc:
        if get_settings().environment == "production":
            raise ApiError(
                503,
                "RATE_LIMIT_UNAVAILABLE",
                "The service is temporarily unavailable.",
            ) from exc
        return
    if count > limit:
        raise ApiError(429, "RATE_LIMITED", "Too many attempts. Please wait and try again.")
