#!/usr/bin/env python3
"""Entry point to start the arq background worker.

Usage:
    python run_worker.py
"""
import asyncio
import sys

from app.core.config import settings
from app.core.logging import setup_logging


async def main() -> None:
    setup_logging(debug=settings.DEBUG, app_env=settings.APP_ENV)

    from arq.connections import RedisSettings
    from arq import create_pool

    from app.jobs import WorkerSettings

    redis = await create_pool(RedisSettings.from_dsn(settings.REDIS_URL))

    worker = WorkerSettings()
    worker.redis = redis
    worker.poll_delay = 0.5  # seconds between queue polls
    worker.burst = False

    # Run until interrupted
    from arq.worker import Worker as ArqWorker

    arq_worker = ArqWorker(
        functions=worker.functions,
        redis_pool=redis,
        poll_delay=worker.poll_delay,
        burst=worker.burst,
    )

    print(f"Worker started, polling {settings.REDIS_URL}", flush=True)
    try:
        await arq_worker.async_run()
    except KeyboardInterrupt:
        pass
    finally:
        await redis.close()


if __name__ == "__main__":
    asyncio.run(main())
