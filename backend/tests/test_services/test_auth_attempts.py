import pytest

from app.services import auth_attempts


class FakeRedis:
    def __init__(self):
        self.values = {}
        self.ttls = {}

    async def exists(self, key):
        return int(key in self.values)

    async def ttl(self, key):
        return self.ttls.get(key, -1)

    async def incr(self, key):
        self.values[key] = int(self.values.get(key, 0)) + 1
        return self.values[key]

    async def expire(self, key, ttl):
        self.ttls[key] = ttl

    async def setex(self, key, ttl, value):
        self.values[key] = value
        self.ttls[key] = ttl

    async def delete(self, key):
        self.values.pop(key, None)
        self.ttls.pop(key, None)


def fake_get_redis(redis):
    async def _get_redis():
        return redis

    return _get_redis


@pytest.mark.anyio
async def test_record_failed_login_locks_after_threshold(monkeypatch):
    redis = FakeRedis()
    monkeypatch.setattr(auth_attempts, "get_redis", fake_get_redis(redis))
    monkeypatch.setattr(auth_attempts.settings, "LOGIN_MAX_ATTEMPTS", 2)
    monkeypatch.setattr(auth_attempts.settings, "LOGIN_LOCKOUT_MINUTES", 15)

    assert await auth_attempts.record_failed_login("alice") == 1
    assert await auth_attempts.check_login_locked("alice") is False

    assert await auth_attempts.record_failed_login("alice") == 2
    assert await auth_attempts.check_login_locked("alice") is True


@pytest.mark.anyio
async def test_clear_login_attempts_removes_attempt_and_lockout(monkeypatch):
    redis = FakeRedis()
    monkeypatch.setattr(auth_attempts, "get_redis", fake_get_redis(redis))
    monkeypatch.setattr(auth_attempts.settings, "LOGIN_MAX_ATTEMPTS", 1)

    await auth_attempts.record_failed_login("bob")
    assert await auth_attempts.check_login_locked("bob") is True

    await auth_attempts.clear_login_attempts("bob")

    assert await auth_attempts.check_login_locked("bob") is False
