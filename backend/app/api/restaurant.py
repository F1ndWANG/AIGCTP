"""Restaurant recommendation API — standalone and saved recommendation endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.models.restaurant import RestaurantRecommendation
from app.agents.restaurant_agent import recommend_restaurants, recommend_nearby
from app.agents.domain_results import to_legacy_payload
from app.schemas.restaurant import RestaurantRecommendationResponse, RestaurantSelectionRequest

router = APIRouter(prefix="/restaurant", tags=["restaurant"])


class RecommendRequest(BaseModel):
    city: str
    cuisine: Optional[str] = None
    dietary_restrictions: Optional[list[str]] = None
    session_id: Optional[str] = None


class NearbyRequest(BaseModel):
    lat: float
    lng: float
    radius: int = 1000
    types: Optional[str] = None
    session_id: Optional[str] = None


async def save_restaurant_recommendation(
    db: AsyncSession,
    user_id: int,
    session_id: str | None,
    city: str,
    query: str,
    result: dict,
) -> RestaurantRecommendation:
    record = RestaurantRecommendation(
        user_id=user_id,
        session_id=session_id,
        city=city or result.get("city", ""),
        query=query,
        response=result.get("response", ""),
        restaurants=result.get("restaurants", []) or [],
    )
    db.add(record)
    await db.flush()
    return record


@router.post("/recommend")
async def restaurant_recommend(
    payload: RecommendRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """推荐指定城市的餐厅，并保存推荐列表。"""
    result = to_legacy_payload(await recommend_restaurants(
        city=payload.city,
        user_message=f"推荐{payload.city}的{' '.join(payload.dietary_restrictions or [])}餐厅",
        dietary_restrictions=payload.dietary_restrictions,
        cuisine=payload.cuisine,
    ))
    record = await save_restaurant_recommendation(
        db=db,
        user_id=current_user.id,
        session_id=payload.session_id,
        city=payload.city,
        query=payload.cuisine or payload.city,
        result=result,
    )
    await db.commit()
    result["recommendation_id"] = record.id
    return result


@router.post("/nearby")
async def restaurant_nearby(
    payload: NearbyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """推荐当前位置附近的餐厅，并保存推荐列表。"""
    result = to_legacy_payload(await recommend_nearby(
        latitude=payload.lat,
        longitude=payload.lng,
        user_message="附近有什么好吃的",
        radius=payload.radius,
        types=payload.types,
    ))
    record = await save_restaurant_recommendation(
        db=db,
        user_id=current_user.id,
        session_id=payload.session_id,
        city=result.get("city", ""),
        query=f"{payload.lat},{payload.lng}",
        result=result,
    )
    await db.commit()
    result["recommendation_id"] = record.id
    return result


@router.get("/recommendations", response_model=list[RestaurantRecommendationResponse])
async def list_recommendations(
    session_id: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(RestaurantRecommendation).where(RestaurantRecommendation.user_id == current_user.id)
    if session_id:
        query = query.where(RestaurantRecommendation.session_id == session_id)
    query = query.order_by(RestaurantRecommendation.updated_at.desc())
    result = await db.execute(query)
    return [RestaurantRecommendationResponse.model_validate(row) for row in result.scalars().all()]


@router.get("/recommendations/{recommendation_id}", response_model=RestaurantRecommendationResponse)
async def get_recommendation(
    recommendation_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(RestaurantRecommendation).where(
            RestaurantRecommendation.id == recommendation_id,
            RestaurantRecommendation.user_id == current_user.id,
        )
    )
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="Restaurant recommendation not found")
    return RestaurantRecommendationResponse.model_validate(record)


@router.post("/recommendations/{recommendation_id}/select", response_model=RestaurantRecommendationResponse)
async def select_recommendation_restaurant(
    recommendation_id: int,
    payload: RestaurantSelectionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(RestaurantRecommendation).where(
            RestaurantRecommendation.id == recommendation_id,
            RestaurantRecommendation.user_id == current_user.id,
        )
    )
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="Restaurant recommendation not found")
    record.selected_restaurant = payload.restaurant
    await db.commit()
    await db.refresh(record)
    return RestaurantRecommendationResponse.model_validate(record)


@router.delete("/recommendations/{recommendation_id}", status_code=204)
async def delete_recommendation(
    recommendation_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(RestaurantRecommendation).where(
            RestaurantRecommendation.id == recommendation_id,
            RestaurantRecommendation.user_id == current_user.id,
        )
    )
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="Restaurant recommendation not found")
    await db.delete(record)
    await db.commit()
