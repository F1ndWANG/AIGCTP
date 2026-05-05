"""Rate limiting middleware using Redis with graceful degradation."""
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.redis import get_redis
from app.core.config import settings


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for health check
        if request.url.path == "/health":
            return await call_next(request)

        client_id = request.headers.get(
            "X-Forwarded-For",
            request.client.host if request.client else "unknown",
        )

        r = await get_redis()
        if r:
            key = f"ratelimit:{client_id}"
            count = await r.incr(key)
            if count == 1:
                await r.expire(key, 60)

            if count > settings.RATE_LIMIT_PER_MINUTE:
                raise HTTPException(
                    status_code=429,
                    detail="请求过于频繁，请稍后再试",
                )

        return await call_next(request)
