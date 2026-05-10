from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.diet import HealthProfile, MealRecord, DietPlan
from app.schemas.diet import (
    HealthProfileRequest,
    HealthProfileResponse,
    MealRecordRequest,
    MealRecordResponse,
    MealRecordListResponse,
    DietPlanResponse,
    DietPlanListItem,
)

router = APIRouter(prefix="/diet", tags=["diet"])


# --- Health Profile ---


@router.get("/profile", summary="Get health profile", response_model=HealthProfileResponse)
async def get_health_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(HealthProfile).where(HealthProfile.user_id == current_user.id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Health profile not found")
    return HealthProfileResponse.model_validate(profile)


@router.put("/profile", summary="Update health profile", response_model=HealthProfileResponse)
async def update_health_profile(
    payload: HealthProfileRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(HealthProfile).where(HealthProfile.user_id == current_user.id)
    )
    profile = result.scalar_one_or_none()

    if profile:
        for field in ("height", "weight", "age", "gender", "allergies", "chronic_conditions", "diet_goals", "dietary_restrictions"):
            val = getattr(payload, field, None)
            if val is not None:
                setattr(profile, field, val)
    else:
        profile = HealthProfile(
            user_id=current_user.id,
            height=payload.height,
            weight=payload.weight,
            age=payload.age,
            gender=payload.gender,
            allergies=payload.allergies,
            chronic_conditions=payload.chronic_conditions,
            diet_goals=payload.diet_goals,
            dietary_restrictions=payload.dietary_restrictions,
        )
        db.add(profile)

    await db.commit()
    await db.refresh(profile)
    return HealthProfileResponse.model_validate(profile)


# --- Meal Records ---


@router.get("/meals", summary="List meal records", response_model=list[MealRecordResponse])
async def list_meals(
    meal_date: date | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(MealRecord).where(MealRecord.user_id == current_user.id)
    if meal_date:
        query = query.where(MealRecord.date == meal_date)
    query = query.order_by(MealRecord.date.desc(), MealRecord.created_at.asc()).limit(50)

    result = await db.execute(query)
    records = result.scalars().all()
    return [MealRecordResponse.model_validate(r) for r in records]


@router.get("/meals/summary", summary="Get meal nutrition summary", response_model=MealRecordListResponse)
async def get_meal_summary(
    meal_date: date | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(MealRecord).where(MealRecord.user_id == current_user.id)
    if meal_date:
        query = query.where(MealRecord.date == meal_date)
    else:
        query = query.where(MealRecord.date == date.today())
    query = query.order_by(MealRecord.created_at.asc())

    result = await db.execute(query)
    records = result.scalars().all()

    total_calories = 0.0
    total_protein = 0.0
    total_carbs = 0.0
    total_fat = 0.0
    for r in records:
        if r.total_nutrition:
            total_calories += r.total_nutrition.get("calories", 0) or 0
            total_protein += r.total_nutrition.get("protein", 0) or 0
            total_carbs += r.total_nutrition.get("carbs", 0) or 0
            total_fat += r.total_nutrition.get("fat", 0) or 0

    return MealRecordListResponse(
        records=[MealRecordResponse.model_validate(r) for r in records],
        total_calories=total_calories,
        total_protein=total_protein,
        total_carbs=total_carbs,
        total_fat=total_fat,
    )


@router.post("/meals", summary="Create meal record", response_model=MealRecordResponse, status_code=201)
async def create_meal(
    payload: MealRecordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    record = MealRecord(
        user_id=current_user.id,
        date=payload.date,
        meal_type=payload.meal_type,
        foods=payload.foods,
        total_nutrition=payload.total_nutrition,
        notes=payload.notes,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return MealRecordResponse.model_validate(record)


@router.delete("/meals/{meal_id}", summary="Delete meal record", status_code=204)
async def delete_meal(
    meal_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(MealRecord).where(MealRecord.id == meal_id, MealRecord.user_id == current_user.id)
    )
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="Meal record not found")
    await db.delete(record)
    await db.commit()


# --- Diet Plans ---


@router.get("/plans", summary="List diet plans", response_model=list[DietPlanListItem])
async def list_diet_plans(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(DietPlan)
        .where(DietPlan.user_id == current_user.id)
        .order_by(DietPlan.created_at.desc())
        .limit(50)
    )
    plans = result.scalars().all()
    return [DietPlanListItem.model_validate(p) for p in plans]


@router.get("/plans/{plan_id}", summary="Get diet plan detail", response_model=DietPlanResponse)
async def get_diet_plan(
    plan_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(DietPlan).where(DietPlan.id == plan_id, DietPlan.user_id == current_user.id)
    )
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Diet plan not found")
    return DietPlanResponse.model_validate(plan)


@router.post("/plans/{plan_id}/confirm", summary="Confirm diet plan", response_model=DietPlanResponse)
async def confirm_diet_plan(
    plan_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(DietPlan).where(DietPlan.id == plan_id, DietPlan.user_id == current_user.id)
    )
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Diet plan not found")

    plan.status = "active"
    if not plan.activated_at:
        plan.activated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    await db.commit()
    await db.refresh(plan)
    return DietPlanResponse.model_validate(plan)


@router.delete("/plans/{plan_id}", summary="Delete diet plan", status_code=204)
async def delete_diet_plan(
    plan_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(DietPlan).where(DietPlan.id == plan_id, DietPlan.user_id == current_user.id)
    )
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Diet plan not found")
    await db.delete(plan)
    await db.commit()
