"""Rate limiting middleware using Redis with graceful degradation.

Supports:
- Differentiated limits per endpoint pattern (auth / chat / default)
- Trusted proxy chain for X-Forwarded-For
- Standard rate-limit response headers
- Graceful degradation when Redis is unavailable
"""
import ipaddress
import time

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.redis import get_redis
from app.core.config import settings
from app.core.error_codes import ERR_RATE_LIMITED
from app.core.http_paths import RATE_LIMIT_EXEMPT_PATHS


_ENDPOINT_LIMITS: list[tuple[str, int]] = [
    ("/auth/", settings.RATE_LIMIT_AUTH_PER_MINUTE),  # 5/min
    ("/chat/", settings.RATE_LIMIT_CHAT_PER_MINUTE),  # 30/min
    ("/", settings.RATE_LIMIT_PER_MINUTE),             # 60/min (fallback)
]


def _get_client_ip(request: Request) -> str:
    """Extract the real client IP, respecting trusted proxies."""
    forwarded = request.headers.get("X-Forwarded-For", "")
    if not forwarded:
        return request.client.host if request.client else "unknown"

    trusted = settings.trusted_proxies_list

    # Parse the chain: "client, proxy1, proxy2"
    ips = [ip.strip() for ip in forwarded.split(",") if ip.strip()]
    if not ips:
        return request.client.host if request.client else "unknown"

    if not trusted:
        # No trusted proxies configured: take X-Forwarded-For at face value
        return ips[0]

    # Walk from the rightmost IP, skipping trusted proxies
    for ip in reversed(ips):
        try:
            addr = ipaddress.ip_address(ip)
            is_trusted = any(
                ipaddress.ip_address(addr) in ipaddress.ip_network(t)
                for t in trusted
            )
            if not is_trusted:
                return ip
        except ValueError:
            continue

    # All proxies were trusted, fall back to the leftmost
    return ips[0]


def _get_limit_for_path(path: str) -> int:
    for prefix, limit in _ENDPOINT_LIMITS:
        if path.startswith(prefix):
            return limit
    return settings.RATE_LIMIT_PER_MINUTE


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Local development uses an in-memory Redis fallback and frequent browser
        # refreshes/tests can exhaust the shared IP bucket quickly. Keep hard rate
        # limits for production, but do not block the developer login loop.
        if not settings.is_production and not settings.TESTING:
            return await call_next(request)

        # Skip rate limiting for health checks
        if request.url.path in RATE_LIMIT_EXEMPT_PATHS:
            return await call_next(request)

        client_id = _get_client_ip(request)
        limit = _get_limit_for_path(request.url.path)

        r = await get_redis()
        if r:
            try:
                key = f"ratelimit:{client_id}:{request.url.path}"
                count = await r.incr(key)
                await r.expire(key, 60)  # ensure TTL even if key existed without one
                remaining = max(0, limit - count)

                ttl = await r.ttl(key)
                if ttl < 0:
                    ttl = 60

                if count > limit:
                    from fastapi.responses import JSONResponse

                    resp = JSONResponse(
                        content={"error": ERR_RATE_LIMITED.code, "detail": ERR_RATE_LIMITED.message},
                        status_code=429,
                        headers={
                            "X-RateLimit-Limit": str(limit),
                            "X-RateLimit-Remaining": "0",
                            "X-RateLimit-Reset": str(int(time.time() + ttl)),
                            "Retry-After": str(ttl),
                        },
                    )
                    return resp

                response = await call_next(request)
                response.headers["X-RateLimit-Limit"] = str(limit)
                response.headers["X-RateLimit-Remaining"] = str(remaining)
                response.headers["X-RateLimit-Reset"] = str(int(time.time() + ttl))
                return response

            except Exception:
                # Redis is optional; do not fail user requests
                logger = __import__("logging").getLogger("app.middleware.rate_limit")
                logger.exception("Rate limit check failed (Redis error)")
                pass

        return await call_next(request)
