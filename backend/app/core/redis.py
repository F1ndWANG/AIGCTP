"""Redis client - optional for dev, hardens gracefully when unavailable.

Features:
- Graceful degradation when Redis is unavailable
- Periodic retry (30s interval) so app auto-reconnects when Redis comes back
- Connection pool with max_connections=10
- Initialization protected by asyncio.Lock() to prevent race on globals
"""
import asyncio
import time
from urllib.parse import unquote, urlparse

from app.core.config import settings

_redis_available = True
_redis_client = None
_memory_client = None
_last_ping_failure = 0.0
_RETRY_INTERVAL = 30.0
_init_lock = asyncio.Lock()


class InMemoryRedis:
    """Small async Redis-compatible fallback for local development only."""

    def __init__(self):
        self._store: dict[str, tuple[str, float | None]] = {}

    def __bool__(self) -> bool:
        return True

    def _purge_expired(self, key: str) -> None:
        item = self._store.get(key)
        if not item:
            return
        _, expires_at = item
        if expires_at is not None and expires_at <= time.monotonic():
            self._store.pop(key, None)

    async def ping(self) -> bool:
        return True

    async def get(self, key: str):
        self._purge_expired(key)
        item = self._store.get(key)
        return item[0] if item else None

    async def setex(self, key: str, ttl: int, value) -> bool:
        self._store[key] = (str(value), time.monotonic() + ttl)
        return True

    async def delete(self, *keys: str) -> int:
        deleted = 0
        for key in keys:
            self._purge_expired(key)
            if key in self._store:
                deleted += 1
                self._store.pop(key, None)
        return deleted

    async def exists(self, key: str) -> int:
        self._purge_expired(key)
        return 1 if key in self._store else 0

    async def incr(self, key: str) -> int:
        self._purge_expired(key)
        value, expires_at = self._store.get(key, ("0", None))
        count = int(value) + 1
        self._store[key] = (str(count), expires_at)
        return count

    async def expire(self, key: str, ttl: int) -> bool:
        self._purge_expired(key)
        if key not in self._store:
            return False
        value, _ = self._store[key]
        self._store[key] = (value, time.monotonic() + ttl)
        return True

    async def ttl(self, key: str) -> int:
        self._purge_expired(key)
        item = self._store.get(key)
        if not item:
            return -2
        _, expires_at = item
        if expires_at is None:
            return -1
        return max(0, int(expires_at - time.monotonic()))

    async def close(self) -> None:
        self._store.clear()


def _get_memory_client():
    global _memory_client
    if _memory_client is None:
        _memory_client = InMemoryRedis()
    return _memory_client


def _client_options_from_url(redis_url: str) -> dict:
    parsed = urlparse(redis_url)
    if parsed.scheme == "memory":
        return {"memory": True}
    if parsed.scheme not in {"redis", "rediss"}:
        raise ValueError(f"Unsupported Redis URL scheme: {parsed.scheme}")

    db = 0
    if parsed.path and parsed.path != "/":
        db = int(parsed.path.lstrip("/") or "0")

    return {
        "host": parsed.hostname or "localhost",
        "port": parsed.port or 6379,
        "db": db,
        "username": unquote(parsed.username) if parsed.username else None,
        "password": unquote(parsed.password) if parsed.password else None,
        "ssl": parsed.scheme == "rediss",
    }


async def get_redis():
    global _redis_client, _redis_available, _last_ping_failure

    if not _redis_available:
        if time.monotonic() - _last_ping_failure < _RETRY_INTERVAL:
            return None if settings.is_production else _get_memory_client()
        _redis_available = True

    if _redis_client is not None:
        return _redis_client

    async with _init_lock:
        # Double-check after acquiring lock
        if _redis_client is not None:
            return _redis_client

        try:
            from redis.asyncio import Redis

            client_options = _client_options_from_url(settings.REDIS_URL)
            if client_options.pop("memory", False):
                return _get_memory_client()

            _redis_client = Redis(
                **client_options,
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=2,
                socket_keepalive=True,
                max_connections=settings.REDIS_MAX_CONNECTIONS,
            )
            await _redis_client.ping()
        except Exception as e:
            _redis_available = False
            _last_ping_failure = time.monotonic()
            _redis_client = None
            import logging
            logging.getLogger("app.core.redis").warning("Redis unavailable: %s", e)
            return None if settings.is_production else _get_memory_client()
    return _redis_client


async def close_redis():
    global _redis_client, _memory_client, _redis_available
    if _redis_client:
        try:
            await _redis_client.close()
        except Exception:
            pass
        _redis_client = None
    if _memory_client:
        await _memory_client.close()
        _memory_client = None
    _redis_available = True
