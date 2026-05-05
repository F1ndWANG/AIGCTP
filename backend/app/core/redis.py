"""Redis client - optional for dev, hardens gracefully when unavailable.

Features:
- Graceful degradation when Redis is unavailable
- Periodic retry (30s interval) so app auto-reconnects when Redis comes back
- Connection pool with max_connections=10
"""
import time

from app.core.config import settings

_redis_available = True
_redis_client = None
_last_ping_failure = 0.0
_RETRY_INTERVAL = 30.0


async def get_redis():
    global _redis_client, _redis_available, _last_ping_failure

    if not _redis_available:
        if time.monotonic() - _last_ping_failure < _RETRY_INTERVAL:
            return None
        _redis_available = True

    if _redis_client is None:
        try:
            from redis.asyncio import Redis

            _redis_client = Redis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                socket_connect_timeout=2,
                socket_keepalive=True,
                max_connections=10,
            )
            await _redis_client.ping()
        except Exception as e:
            _redis_available = False
            _last_ping_failure = time.monotonic()
            _redis_client = None
            return None
    return _redis_client


async def close_redis():
    global _redis_client, _redis_available
    if _redis_client:
        try:
            await _redis_client.close()
        except Exception:
            pass
        _redis_client = None
        _redis_available = True
