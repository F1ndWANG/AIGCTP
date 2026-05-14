"""Travel plan persistence operations used by API and agents."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.travel import TravelPlan
from app.services.recommendation import recommendation_service


class TravelPlanNotFoundError(Exception):
    pass


async def list_user_travel_plans(db: AsyncSession, *, user_id: int, limit: int = 50) -> list[TravelPlan]:
    result = await db.execute(
        select(TravelPlan)
        .where(TravelPlan.user_id == user_id)
        .order_by(TravelPlan.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_user_travel_plan(db: AsyncSession, *, user_id: int, plan_id: int) -> TravelPlan:
    result = await db.execute(
        select(TravelPlan).where(TravelPlan.id == plan_id, TravelPlan.user_id == user_id)
    )
    plan = result.scalar_one_or_none()
    if not plan:
        raise TravelPlanNotFoundError
    return plan


async def confirm_user_travel_plan(db: AsyncSession, *, user_id: int, plan_id: int) -> TravelPlan:
    plan = await get_user_travel_plan(db, user_id=user_id, plan_id=plan_id)
    plan.status = "confirmed"
    await recommendation_service.track(
        db,
        user_id=user_id,
        domain="travel",
        item_type="travel_plan",
        item_id=plan.id,
        event_type="confirm_plan",
        context={
            "destination": plan.destination,
            "days": plan.days,
            "preferences": plan.preferences or {},
        },
        commit=False,
    )
    await db.commit()
    await db.refresh(plan)
    return plan


async def delete_user_travel_plan(db: AsyncSession, *, user_id: int, plan_id: int) -> None:
    plan = await get_user_travel_plan(db, user_id=user_id, plan_id=plan_id)
    await db.delete(plan)
    await db.commit()
