"""
Async job definitions for the arq worker.

Long-running operations (travel planning, diet plan generation) are offloaded
from the HTTP request path into background jobs for better UX and scalability.

Each job function:
  1. Opens its own database session
  2. Executes domain logic
  3. Persists results
  4. Returns a serializable result dict

The arq worker (run_worker.py) discovers these functions via WorkerSettings.
"""
from __future__ import annotations

from typing import Any

from app.core.database import async_session as async_session_maker
from app.core.logging import get_logger

logger = get_logger(__name__)


async def plan_trip_job(ctx: dict[str, Any], user_id: int, **kwargs: Any) -> dict[str, Any]:
    """Generate a travel plan as a background job."""
    from app.agents.travel_agent import plan_trip
    from app.services.runtime import create_task_run, mark_task_succeeded, mark_task_failed

    async with async_session_maker() as db:
        task = await create_task_run(
            db=db, user_id=user_id,
            session_id=kwargs.get("session_id", ""),
            task_type="travel_plan_background",
            input_payload=kwargs, max_retries=2,
        )
        await db.commit()

    try:
        async with async_session_maker() as db:
            result = await plan_trip(
                destination=kwargs.get("destination", ""),
                days=kwargs.get("days", 3),
                user_id=user_id,
                db=db,
                user_preferences=kwargs.get("user_preferences", {}),
                original_message=kwargs.get("original_message", ""),
                conversation_messages=kwargs.get("conversation_messages", []),
                avoid_pois=kwargs.get("avoid_pois", []),
            )
    except Exception as e:
        logger.error("plan_trip_job failed: %s", e)
        async with async_session_maker() as db:
            await mark_task_failed(task, error=str(e)[:2000])
            await db.commit()
        return {"error": str(e)[:500]}

    async with async_session_maker() as db:
        await mark_task_succeeded(task, result_payload={"plan_id": getattr(result, "travel_plan_id", None)})
        await db.commit()

    return result.to_legacy() if hasattr(result, "to_legacy") else {"response": str(result)}


async def generate_diet_plan_job(ctx: dict[str, Any], user_id: int, **kwargs: Any) -> dict[str, Any]:
    """Generate a diet plan as a background job."""
    from app.agents.diet_agent import recommend_diet
    from sqlalchemy import select
    from app.models.diet import HealthProfile, MealRecord

    async with async_session_maker() as db:
        hp_r = await db.execute(select(HealthProfile).where(HealthProfile.user_id == user_id))
        hp = hp_r.scalar_one_or_none()
        meals_r = await db.execute(
            select(MealRecord).where(MealRecord.user_id == user_id)
            .order_by(MealRecord.date.desc()).limit(14)
        )
        recent_meals = list(meals_r.scalars().all())

    async with async_session_maker() as db:
        result = await recommend_diet(
            user_message=kwargs.get("user_message", ""),
            user_id=user_id,
            db=db,
            health_profile=hp,
            meal_records=recent_meals,
            wants_plan=kwargs.get("wants_plan", True),
        )

    payload = result.to_legacy() if hasattr(result, "to_legacy") else {"response": str(result)}
    return payload


async def background_chat_job(
    ctx: dict[str, Any],
    *,
    user_id: int,
    session_id: str,
    message: str,
    travel_plan_id: int | None = None,
    task_id: str | None = None,
) -> dict[str, Any]:
    """Run the full chat flow as a background job.

    This lets the HTTP handler return immediately while the worker
    handles conversation, agent dispatch, and artifact persistence.
    The client polls ``GET /api/v1/runtime/tasks/{task_id}`` for the result.
    """
    from app.schemas.travel import ChatRequest
    from app.services.chat_orchestrator import handle_chat
    from app.models.user import User
    from app.models.runtime import TaskRun
    from sqlalchemy import select

    async with async_session_maker() as db:
        # Load caller
        user_r = await db.execute(select(User).where(User.id == user_id))
        user = user_r.scalar_one_or_none()
        if user is None:
            return {"error": "user_not_found"}

        # Load existing task_run created by the HTTP handler
        task = None
        if task_id:
            tr = await db.execute(select(TaskRun).where(TaskRun.task_id == task_id))
            task = tr.scalar_one_or_none()

        payload = ChatRequest(
            session_id=session_id or "",
            message=message,
            travel_plan_id=travel_plan_id,
        )

        try:
            response = await handle_chat(payload, user, db, existing_task=task)
            result = response.model_dump(mode="json") if hasattr(response, "model_dump") else {"message": str(response)}
            return {"status": "succeeded", "result": result}
        except Exception as e:
            logger.error("background_chat_job failed: %s", e)
            return {"status": "failed", "error": str(e)[:500]}


# ── arq WorkerSettings ─────────────────────────────────────────

class WorkerSettings:
    """arq WorkerSettings — consumed by `arq run` CLI or run_worker.py."""

    functions = [plan_trip_job, generate_diet_plan_job, background_chat_job]
    redis_settings = None  # populated at runtime

    @classmethod
    def from_settings(cls, redis_url: str) -> type[WorkerSettings]:
        from arq.connections import RedisSettings
        cls.redis_settings = RedisSettings.from_dsn(redis_url)
        return cls
