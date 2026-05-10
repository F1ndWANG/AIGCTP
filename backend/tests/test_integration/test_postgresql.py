"""PostgreSQL integration tests.

These tests verify behaviour that relies on PostgreSQL-specific features
(JSONB operators, full-text search, etc.) and catch incompatibilities that
SQLite-in-memory tests would miss.

They are **skipped automatically** when no PostgreSQL instance is available.
To run locally::

    DATABASE_URL=postgresql+asyncpg://lifeai:lifeai_dev@localhost:5432/life_recommender_test \\
    pytest tests/test_integration/ -v
"""
import asyncio
import os
import sys
import pytest
from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

# asyncpg requires SelectorEventLoop on Windows (ProactorEventLoop is incompatible)
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from app.core.database import Base
from app.models.user import User
from app.models.conversation import Conversation
from app.models.travel import TravelPlan
from app.models.diet import DietPlan
from app.models.runtime import TaskRun, DomainEvent
from app.models.feedback import RecommendationLog

# ── Skip if no PostgreSQL ───────────────────────────────────────

PG_URL = os.environ.get("DATABASE_URL", "")
if PG_URL and not PG_URL.startswith("postgresql"):
    PG_URL = ""  # Only run against real PostgreSQL

pytestmark = pytest.mark.skipif(
    not PG_URL,
    reason="Set DATABASE_URL to a PostgreSQL connection string to run integration tests",
)


@pytest.fixture
async def pg_session():
    """Per-test PostgreSQL session with pre-test cleanup."""
    engine = create_async_engine(PG_URL, echo=False, pool_size=1)

    # Clean all data before test
    async with engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(text(f"TRUNCATE TABLE {table.name} CASCADE"))

    # Ensure schema exists
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    conn = await engine.connect()
    session = AsyncSession(bind=conn, expire_on_commit=False)

    # Seed users needed by tests (FK requirement in PostgreSQL)
    for uid in (1, 2, 3, 10):
        session.add(User(id=uid, username=f"test_user_{uid}", hashed_password="x"))
    await session.commit()

    yield session
    await session.close()
    await conn.close()
    await engine.dispose()


# ── Tests ───────────────────────────────────────────────────────


class TestConversationPersistence:
    """Verify conversation save/load round-trips through PostgreSQL."""

    async def test_save_and_load_conversation(self, pg_session):
        conv = Conversation(
            session_id="pg-test-session-1",
            user_id=1,
            title="PG Integration Test",
            messages=[{"role": "user", "content": "你好"}],
            context={"key": "value"},
        )
        pg_session.add(conv)
        await pg_session.commit()

        result = await pg_session.execute(
            select(Conversation).where(Conversation.session_id == "pg-test-session-1")
        )
        loaded = result.scalar_one()
        assert loaded.title == "PG Integration Test"
        assert loaded.messages == [{"role": "user", "content": "你好"}]
        assert loaded.context == {"key": "value"}

    async def test_conversation_message_list_ordering(self, pg_session):
        conv = Conversation(
            session_id="pg-msg-order",
            user_id=1,
            title="Message Order",
            messages=[
                {"role": "user", "content": "first"},
                {"role": "assistant", "content": "second"},
                {"role": "user", "content": "third"},
            ],
        )
        pg_session.add(conv)
        await pg_session.commit()

        result = await pg_session.execute(
            select(Conversation).where(Conversation.session_id == "pg-msg-order")
        )
        loaded = result.scalar_one()
        assert len(loaded.messages) == 3
        assert loaded.messages[0]["content"] == "first"
        assert loaded.messages[2]["content"] == "third"


class TestTravelPlanPersistence:
    """Verify travel plan schema works with PostgreSQL."""

    async def test_create_travel_plan(self, pg_session):
        plan = TravelPlan(
            user_id=1,
            destination="北京",
            days=3,
            itinerary={"day_by_day": [{"day": 1, "theme": "故宫"}]},
            status="active",
        )
        pg_session.add(plan)
        await pg_session.commit()
        await pg_session.refresh(plan)

        assert plan.id is not None
        assert plan.destination == "北京"
        assert plan.itinerary["day_by_day"][0]["theme"] == "故宫"

    async def test_travel_plan_status_filter(self, pg_session):
        for i, status in enumerate(["active", "active", "archived"]):
            pg_session.add(TravelPlan(user_id=2, destination=f"城市{i}", days=2, status=status))
        await pg_session.commit()

        result = await pg_session.execute(
            select(TravelPlan).where(
                TravelPlan.user_id == 2, TravelPlan.status == "active"
            )
        )
        plans = list(result.scalars().all())
        assert len(plans) == 2

    async def test_travel_plan_jsonb_itinerary(self, pg_session):
        """PostgreSQL JSONB preserves nested structure."""
        complex_itinerary = {
            "day_by_day": [
                {
                    "day": 1,
                    "theme": "文化探索",
                    "weather": {"condition": "晴", "temp_min": "20", "temp_max": "30"},
                    "activities": [
                        {"time": "09:00", "poi": "故宫", "duration": "3h"},
                        {"time": "14:00", "poi": "天坛", "duration": "2h"},
                    ],
                    "meals": [
                        {"type": "午餐", "restaurant": "全聚德", "recommendation": "烤鸭"},
                    ],
                    "hotel": {"name": "北京饭店", "rating": 4.5},
                    "shopping": [],
                    "transport_tips": "地铁方便",
                },
            ],
            "budget_estimate": {"total": 2000, "breakdown": {"住宿": 800, "餐饮": 500}},
            "tips": ["提前预约", "带好证件"],
        }
        plan = TravelPlan(
            user_id=3,
            destination="北京",
            days=1,
            itinerary=complex_itinerary,
            status="active",
        )
        pg_session.add(plan)
        await pg_session.commit()
        await pg_session.refresh(plan)

        loaded_itinerary = plan.itinerary
        assert loaded_itinerary["day_by_day"][0]["activities"][0]["poi"] == "故宫"
        assert loaded_itinerary["budget_estimate"]["total"] == 2000
        assert len(loaded_itinerary["tips"]) == 2


class TestTaskRunLifecycle:
    """Verify TaskRun persistence through status transitions."""

    async def test_task_run_crud(self, pg_session):
        task = TaskRun(
            task_id="pg-task-001",
            user_id=1,
            session_id="pg-session-1",
            task_type="chat",
            status="running",
            input={"message": "test"},
        )
        pg_session.add(task)
        await pg_session.commit()

        # Status transition
        result = await pg_session.execute(
            select(TaskRun).where(TaskRun.task_id == "pg-task-001")
        )
        loaded = result.scalar_one()
        assert loaded.status == "running"

        loaded.status = "succeeded"
        loaded.result = {"response": "done"}
        await pg_session.commit()

        result = await pg_session.execute(
            select(TaskRun).where(TaskRun.task_id == "pg-task-001")
        )
        updated = result.scalar_one()
        assert updated.status == "succeeded"
        assert updated.result == {"response": "done"}

    async def test_task_run_enum_filter(self, pg_session):
        """Verify composite index on (user_id, status) works."""
        for i in range(3):
            pg_session.add(
                TaskRun(
                    task_id=f"pg-filter-{i}",
                    user_id=10,
                    session_id="filter-session",
                    task_type="chat",
                    status="succeeded" if i < 2 else "failed",
                )
            )
        await pg_session.commit()

        result = await pg_session.execute(
            select(TaskRun).where(
                TaskRun.user_id == 10, TaskRun.status == "failed"
            )
        )
        failed = list(result.scalars().all())
        assert len(failed) == 1


class TestDomainEventPersistence:
    """Verify DomainEvent append-only log with PostgreSQL."""

    async def test_emit_and_query_events(self, pg_session):
        for i in range(3):
            pg_session.add(
                DomainEvent(
                    event_id=f"evt-{i}",
                    user_id=1,
                    session_id="evt-session",
                    task_id="evt-task",
                    event_type="chat.completed",
                    aggregate_type="conversation",
                    aggregate_id="evt-session",
                    payload={"index": i},
                )
            )
        await pg_session.commit()

        result = await pg_session.execute(
            select(DomainEvent).where(
                DomainEvent.user_id == 1,
                DomainEvent.event_type == "chat.completed",
            ).order_by(DomainEvent.created_at)
        )
        events = list(result.scalars().all())
        assert len(events) == 3
        assert events[0].payload["index"] == 0
        assert events[2].payload["index"] == 2


class TestRecommendationLogPersistence:
    """Verify feedback/RecommendationLog with PostgreSQL."""

    async def test_feedback_log(self, pg_session):
        log = RecommendationLog(
            user_id=1,
            content_type="travel_plan",
            message_id="msg-001",
            feedback="like",
            content_snapshot={"destination": "北京", "days": 3},
        )
        pg_session.add(log)
        await pg_session.commit()
        await pg_session.refresh(log)

        assert log.id is not None
        assert log.content_snapshot["destination"] == "北京"

    async def test_feedback_filter_by_type(self, pg_session):
        for ct in ["travel_plan", "diet", "restaurant"]:
            pg_session.add(
                RecommendationLog(user_id=2, content_type=ct, feedback="like")
            )
        await pg_session.commit()

        result = await pg_session.execute(
            select(RecommendationLog).where(
                RecommendationLog.user_id == 2,
                RecommendationLog.content_type == "diet",
            )
        )
        logs = list(result.scalars().all())
        assert len(logs) == 1
        assert logs[0].content_type == "diet"
