import asyncio
from typing import Any, Callable

from sqlalchemy import text as sa_text

from app.core.config import settings
from app.core.database import async_session
from app.core.redis import get_redis


APP_VERSION = "0.1.0"


def liveness_report() -> dict[str, str]:
    return {"status": "ok", "app": settings.APP_NAME, "version": APP_VERSION}


async def check_database(session_factory: Callable[..., Any] = async_session) -> dict[str, Any]:
    try:
        async with session_factory() as db:
            await db.execute(sa_text("SELECT 1"))
        return {"database": True}
    except Exception as exc:
        return {"database": False, "database_error": str(exc)[:100]}


async def check_redis(redis_factory: Callable[..., Any] = get_redis) -> dict[str, Any]:
    try:
        redis = await redis_factory()
        if not redis:
            return {"redis": False}
        await redis.ping()
        return {"redis": True, "redis_backend": type(redis).__name__}
    except Exception as exc:
        return {"redis": False, "redis_error": str(exc)[:100]}


def build_readiness_report(checks: dict[str, Any], *, redis_required: bool) -> dict[str, Any]:
    database_ok = bool(checks.get("database"))
    redis_ok = bool(checks.get("redis"))
    ready = database_ok and (redis_ok or not redis_required)
    return {
        "status": "ok" if database_ok and redis_ok else "degraded",
        "ready": ready,
        "redis_required": redis_required,
        "checks": checks,
    }


async def readiness_report(
    *,
    session_factory: Callable[..., Any] = async_session,
    redis_factory: Callable[..., Any] = get_redis,
    redis_required: bool | None = None,
) -> dict[str, Any]:
    checks: dict[str, Any] = {}
    checks.update(await check_database(session_factory))
    checks.update(await check_redis(redis_factory))
    return build_readiness_report(
        checks,
        redis_required=settings.is_production if redis_required is None else redis_required,
    )


async def llm_health_report() -> dict[str, Any]:
    try:
        from app.services.llm import llm_service

        await asyncio.wait_for(
            llm_service.client.chat.completions.create(
                model=llm_service.model,
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=2,
                temperature=0,
                timeout=5,
            ),
            timeout=8,
        )
        return {
            "status": "ok",
            "model": llm_service.model,
            "base_url": settings.LLM_API_BASE,
            "latency_check": "connected",
        }
    except Exception as exc:
        return {
            "status": "error",
            "model": settings.LLM_MODEL,
            "base_url": settings.LLM_API_BASE,
            "error": str(exc)[:200],
        }
