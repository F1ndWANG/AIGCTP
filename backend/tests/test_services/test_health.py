from app.services.health import build_readiness_report, check_redis, liveness_report


class FakeRedis:
    async def ping(self):
        return True


class BrokenRedis:
    async def ping(self):
        raise RuntimeError("redis unavailable")


async def test_check_redis_reports_backend_name():
    async def redis_factory():
        return FakeRedis()

    result = await check_redis(redis_factory)

    assert result == {"redis": True, "redis_backend": "FakeRedis"}


async def test_check_redis_handles_missing_or_broken_client():
    async def missing_factory():
        return None

    async def broken_factory():
        return BrokenRedis()

    assert await check_redis(missing_factory) == {"redis": False}
    broken = await check_redis(broken_factory)
    assert broken["redis"] is False
    assert "redis unavailable" in broken["redis_error"]


def test_readiness_allows_redis_degraded_in_development():
    report = build_readiness_report({"database": True, "redis": False}, redis_required=False)

    assert report["ready"] is True
    assert report["status"] == "degraded"


def test_readiness_requires_redis_when_configured():
    report = build_readiness_report({"database": True, "redis": False}, redis_required=True)

    assert report["ready"] is False
    assert report["status"] == "degraded"


def test_liveness_report_is_stable():
    report = liveness_report()

    assert report["status"] == "ok"
    assert report["version"]
