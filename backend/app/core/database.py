from datetime import datetime, timezone
from sqlalchemy import event
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


def _utcnow() -> datetime:
    """Return current UTC datetime for use as Column default."""
    return datetime.now(timezone.utc)


# Slow query threshold (seconds) — queries exceeding this are logged as warnings.
SLOW_QUERY_THRESHOLD = getattr(settings, "SLOW_QUERY_THRESHOLD", 0.5)

connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False
    connect_args["timeout"] = 30

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    connect_args=connect_args,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_timeout=settings.DB_POOL_TIMEOUT,
    pool_pre_ping=True,
    pool_recycle=3600,
)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


if settings.DATABASE_URL.startswith("sqlite"):
    @event.listens_for(engine.sync_engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA synchronous=NORMAL;")
        cursor.execute("PRAGMA busy_timeout=30000;")
        cursor.close()


# ── Slow Query Logging ─────────────────────────────────────────

import time as _time
from app.core.logging import get_logger as _get_logger

_db_logger = _get_logger("app.core.database.slow_query")


@event.listens_for(engine.sync_engine, "before_cursor_execute")
def _before_query(conn, cursor, statement, parameters, context, executemany):
    conn._query_start_time = _time.monotonic()


@event.listens_for(engine.sync_engine, "after_cursor_execute")
def _after_query(conn, cursor, statement, parameters, context, executemany):
    total = _time.monotonic() - conn._query_start_time
    if total > SLOW_QUERY_THRESHOLD:
        # Truncate very long statements for readability
        stmt = statement[:500] if len(statement) > 500 else statement
        _db_logger.warning(
            "Slow query (%.2fs)", total,
            extra={
                "query_time_s": round(total, 3),
                "query": stmt,
                "threshold_s": SLOW_QUERY_THRESHOLD,
            },
        )


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
