"""Cache service - typed Redis cache operations with graceful degradation.

All functions silently return None/False/0 when Redis is unavailable,
so callers don't need to handle Redis failures.
"""
import json
from typing import Any, Optional

from app.core.redis import get_redis
from app.core.config import settings


async def get_json(key: str) -> Optional[dict[str, Any]]:
    """Get a JSON value from cache."""
    r = await get_redis()
    if not r:
        return None
    data = await r.get(key)
    return json.loads(data) if data else None


async def set_json(key: str, value: dict, ttl: Optional[int] = None) -> None:
    """Set a JSON value in cache with TTL (default: REDIS_TTL_DEFAULT)."""
    r = await get_redis()
    if not r:
        return
    ttl = ttl or settings.REDIS_TTL_DEFAULT
    await r.setex(key, ttl, json.dumps(value, ensure_ascii=False, default=str))


async def get_str(key: str) -> Optional[str]:
    """Get a string value from cache."""
    r = await get_redis()
    if not r:
        return None
    return await r.get(key)


async def set_str(key: str, value: str, ttl: Optional[int] = None) -> None:
    """Set a string value in cache with TTL."""
    r = await get_redis()
    if not r:
        return
    ttl = ttl or settings.REDIS_TTL_DEFAULT
    await r.setex(key, ttl, value)


async def get_list(key: str) -> Optional[list]:
    """Get a list value from cache."""
    r = await get_redis()
    if not r:
        return None
    data = await r.get(key)
    return json.loads(data) if data else None


async def set_list(key: str, value: list, ttl: Optional[int] = None) -> None:
    """Set a list value in cache with TTL."""
    r = await get_redis()
    if not r:
        return
    ttl = ttl or settings.REDIS_TTL_DEFAULT
    await r.setex(key, ttl, json.dumps(value, ensure_ascii=False, default=str))


async def delete(key: str) -> None:
    """Delete a key from cache."""
    r = await get_redis()
    if not r:
        return
    await r.delete(key)


async def exists(key: str) -> bool:
    """Check if a key exists in cache."""
    r = await get_redis()
    if not r:
        return False
    return await r.exists(key) > 0


async def incr(key: str, expire: Optional[int] = None) -> int:
    """Increment a counter, optionally setting expiry on first increment."""
    r = await get_redis()
    if not r:
        return 0
    count = await r.incr(key)
    if count == 1 and expire:
        await r.expire(key, expire)
    return count
