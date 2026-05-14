"""Persistence for structured artifacts produced by agents."""
from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.agents.result import AgentResult
from app.models.restaurant import RestaurantRecommendation
from app.models.travel import TravelPlan
from app.schemas.restaurant import RestaurantRecommendationResponse
from app.schemas.travel import ChatResponse, TravelPlanResponse
from app.services.recommendation.catalog import sync_restaurant_recommendation_items, sync_travel_plan_item


async def save_or_update_travel_plan(
    plan_data: dict[str, Any],
    user_id: int,
    travel_plan_id: int | None,
    db: AsyncSession,
) -> tuple[TravelPlanResponse | None, dict[str, Any]]:
    if travel_plan_id:
        result = await db.execute(
            select(TravelPlan).where(
                TravelPlan.id == travel_plan_id,
                TravelPlan.user_id == user_id,
            )
        )
        existing_plan = result.scalar_one_or_none()
        if existing_plan:
            existing_plan.destination = plan_data.get("destination", existing_plan.destination)
            existing_plan.days = plan_data.get("days", existing_plan.days)
            existing_plan.itinerary = plan_data.get("itinerary", existing_plan.itinerary)
            existing_plan.preferences = plan_data.get("preferences", existing_plan.preferences)
            existing_plan.status = "draft"
            flag_modified(existing_plan, "itinerary")
            flag_modified(existing_plan, "preferences")
            await db.flush()
            await sync_travel_plan_item(db, existing_plan)
            await db.refresh(existing_plan)
            return TravelPlanResponse.model_validate(existing_plan), {
                "id": existing_plan.id,
                "destination": existing_plan.destination,
                "days": existing_plan.days,
                "itinerary": existing_plan.itinerary,
            }

    new_plan = TravelPlan(
        user_id=user_id,
        destination=plan_data.get("destination", ""),
        days=plan_data.get("days", 3),
        itinerary=plan_data.get("itinerary", {}),
        preferences=plan_data.get("preferences", {}),
        status="draft",
    )
    db.add(new_plan)
    await db.flush()
    await sync_travel_plan_item(db, new_plan)
    await db.refresh(new_plan)
    return TravelPlanResponse.model_validate(new_plan), {
        "id": new_plan.id,
        "destination": new_plan.destination,
        "days": new_plan.days,
        "itinerary": new_plan.itinerary,
    }


def build_chat_response(
    session_id: str,
    result: AgentResult,
    travel_plan: TravelPlanResponse | None,
) -> ChatResponse:
    return ChatResponse(
        session_id=session_id,
        message=result.response,
        travel_plan=travel_plan,
        products=result.products,
        restaurants=result.restaurants,
        restaurant_recommendation_id=result.restaurant_recommendation_id,
        restaurant_recommendation=result.restaurant_recommendation,
        diet_plan=result.diet_plan,
        cart_items=result.cart_items,
        artifacts=result.artifacts,
    )


async def save_restaurant_recommendation(
    *,
    result: AgentResult,
    user_id: int,
    session_id: str | None,
    query: str,
    db: AsyncSession,
) -> RestaurantRecommendationResponse | None:
    if not result.restaurants or result.restaurant_recommendation_id:
        return None

    record = RestaurantRecommendation(
        user_id=user_id,
        session_id=session_id,
        city=str(result.artifacts.get("city") or ""),
        query=query,
        response=result.response,
        restaurants=result.restaurants,
    )
    db.add(record)
    await db.flush()
    await sync_restaurant_recommendation_items(db, record)
    await db.refresh(record)
    return RestaurantRecommendationResponse.model_validate(record)
