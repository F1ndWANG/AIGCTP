from app.core.config import settings
from app.core.database import async_session, init_db
from app.core.logging import setup_logging
from app.core.redis import close_redis
from app.services.demo_catalog import ensure_demo_catalog


def should_seed_demo_catalog() -> bool:
    """Decide whether startup should seed demo commerce data."""
    if settings.DEMO_CATALOG_AUTO_SEED is not None:
        return settings.DEMO_CATALOG_AUTO_SEED
    return not settings.is_production


async def startup() -> None:
    setup_logging(debug=settings.DEBUG, app_env=settings.APP_ENV)
    await init_db()
    if not should_seed_demo_catalog():
        return
    async with async_session() as db:
        await ensure_demo_catalog(db)


async def shutdown() -> None:
    await close_redis()
