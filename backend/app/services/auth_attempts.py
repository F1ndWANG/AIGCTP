"""Login attempt tracking backed by Redis with graceful degradation."""

from app.core.config import settings
from app.core.redis import get_redis


def _attempt_key(username: str) -> str:
    return f"login_attempts:{username}"


def _lockout_key(username: str) -> str:
    return f"login_lockout:{username}"


async def check_login_locked(username: str) -> bool:
    r = await get_redis()
    if not r:
        return False
    exists = await r.exists(_lockout_key(username))
    if not exists:
        return False
    ttl = await r.ttl(_lockout_key(username))
    return ttl > 0


async def record_failed_login(username: str) -> int:
    """Record a failed login attempt and return the current attempt count."""
    r = await get_redis()
    if not r:
        return 0

    key = _attempt_key(username)
    count = await r.incr(key)
    if count == 1:
        await r.expire(key, settings.LOGIN_LOCKOUT_MINUTES * 60)

    if count >= settings.LOGIN_MAX_ATTEMPTS:
        await r.setex(_lockout_key(username), settings.LOGIN_LOCKOUT_MINUTES * 60, "1")
        await r.delete(key)
        return count

    return count


async def clear_login_attempts(username: str) -> None:
    r = await get_redis()
    if not r:
        return
    await r.delete(_attempt_key(username))
    await r.delete(_lockout_key(username))
