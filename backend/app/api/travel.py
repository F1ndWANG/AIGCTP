from fastapi import APIRouter, HTTPException

from app.api.deps import CurrentUser, DbSession
from app.schemas.travel import TravelPlanResponse, TravelPlanListItem
from app.services.travel_plan_service import (
    TravelPlanNotFoundError,
    confirm_user_travel_plan,
    delete_user_travel_plan,
    get_user_travel_plan,
    list_user_travel_plans,
)

router = APIRouter(prefix="/travel", tags=["travel"])


@router.get("/plans", summary="List travel plans", response_model=list[TravelPlanListItem])
async def list_plans(
    current_user: CurrentUser,
    db: DbSession,
):
    plans = await list_user_travel_plans(db, user_id=current_user.id)
    return [TravelPlanListItem.model_validate(p) for p in plans]


@router.get("/plans/{plan_id}", summary="Get travel plan detail", response_model=TravelPlanResponse)
async def get_plan(
    plan_id: int,
    current_user: CurrentUser,
    db: DbSession,
):
    try:
        plan = await get_user_travel_plan(db, user_id=current_user.id, plan_id=plan_id)
    except TravelPlanNotFoundError:
        raise HTTPException(status_code=404, detail="Travel plan not found")
    return TravelPlanResponse.model_validate(plan)


@router.post("/plans/{plan_id}/confirm", summary="Confirm travel plan", response_model=TravelPlanResponse)
async def confirm_plan(
    plan_id: int,
    current_user: CurrentUser,
    db: DbSession,
):
    try:
        plan = await confirm_user_travel_plan(db, user_id=current_user.id, plan_id=plan_id)
    except TravelPlanNotFoundError:
        raise HTTPException(status_code=404, detail="Travel plan not found")
    return TravelPlanResponse.model_validate(plan)


@router.delete("/plans/{plan_id}", summary="Delete travel plan", status_code=204)
async def delete_plan(
    plan_id: int,
    current_user: CurrentUser,
    db: DbSession,
):
    try:
        await delete_user_travel_plan(db, user_id=current_user.id, plan_id=plan_id)
    except TravelPlanNotFoundError:
        raise HTTPException(status_code=404, detail="Travel plan not found")
