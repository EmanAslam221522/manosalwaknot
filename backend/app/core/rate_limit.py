from fastapi import Request
from redis import Redis

from app.core.config import get_settings
from app.core.errors import ApiError

_redis = Redis.from_url(get_settings().redis_url, decode_responses=True)


def check_redis() -> None:
    _redis.ping()


def enforce_rate_limit(request: Request, scope: str, limit: int, window_seconds: int, subject: str | None = None) -> None:
    client = request.client.host if request.client else "unknown"
    key = f"rate:{scope}:{subject or client}"
    try:
        count = _redis.incr(key)
        if count == 1:
            _redis.expire(key, window_seconds)
    except Exception as exc:
        if get_settings().environment == "production":
            raise ApiError(503, "RATE_LIMIT_UNAVAILABLE", "The service is temporarily unavailable.") from exc
        return
    if count > limit:
        raise ApiError(429, "RATE_LIMITED", "Too many attempts. Please wait and try again.")
