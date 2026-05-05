from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.travel import TravelPlan
from app.schemas.travel import TravelPlanResponse, TravelPlanListItem

router = APIRouter(prefix="/travel", tags=["travel"])


@router.get("/plans", response_model=list[TravelPlanListItem])
async def list_plans(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(TravelPlan)
        .where(TravelPlan.user_id == current_user.id)
        .order_by(TravelPlan.created_at.desc())
        .limit(50)
    )
    plans = result.scalars().all()
    return [TravelPlanListItem.model_validate(p) for p in plans]


@router.get("/plans/{plan_id}", response_model=TravelPlanResponse)
async def get_plan(
    plan_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(TravelPlan).where(TravelPlan.id == plan_id, TravelPlan.user_id == current_user.id)
    )
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Travel plan not found")
    return TravelPlanResponse.model_validate(plan)


@router.delete("/plans/{plan_id}", status_code=204)
async def delete_plan(
    plan_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(TravelPlan).where(TravelPlan.id == plan_id, TravelPlan.user_id == current_user.id)
    )
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Travel plan not found")
    await db.delete(plan)
    await db.commit()
