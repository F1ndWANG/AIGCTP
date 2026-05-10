"""Helpers for enqueuing arq background jobs."""
from __future__ import annotations

from typing import Any

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


async def enqueue_job(job_name: str, **kwargs: Any) -> str | None:
    """Enqueue a job to the arq worker via Redis.

    Returns the arq job ID on success, or None if enqueue failed.
    """
    try:
        from arq.connections import RedisSettings, ArqRedis

        rs = RedisSettings.from_dsn(settings.REDIS_URL)
        redis = await ArqRedis(redis_settings=rs)

        job = await redis.enqueue_job(job_name, **kwargs)
        await redis.close()

        if job is not None:
            return str(job.job_id)
        return None
    except Exception as e:
        logger.warning("Failed to enqueue job %s: %s", job_name, e)
        return None
