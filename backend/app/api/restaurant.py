"""Restaurant recommendation API — standalone endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.api.deps import get_current_user
from app.models.user import User
from app.agents.restaurant_agent import recommend_restaurants, recommend_nearby

router = APIRouter(prefix="/restaurant", tags=["restaurant"])


class RecommendRequest(BaseModel):
    city: str
    cuisine: Optional[str] = None
    dietary_restrictions: Optional[list[str]] = None


class NearbyRequest(BaseModel):
    lat: float
    lng: float
    radius: int = 1000
    types: Optional[str] = None


@router.post("/recommend")
async def restaurant_recommend(
    payload: RecommendRequest,
    current_user: User = Depends(get_current_user),
):
    """推荐指定城市的餐厅"""
    result = await recommend_restaurants(
        city=payload.city,
        user_message=f"推荐{payload.city}的{' '.join(payload.dietary_restrictions or [])}餐厅",
        dietary_restrictions=payload.dietary_restrictions,
        cuisine=payload.cuisine,
    )
    return result


@router.post("/nearby")
async def restaurant_nearby(
    payload: NearbyRequest,
    current_user: User = Depends(get_current_user),
):
    """推荐当前位置附近的餐厅"""
    result = await recommend_nearby(
        latitude=payload.lat,
        longitude=payload.lng,
        user_message="附近有什么好吃的",
        radius=payload.radius,
        types=payload.types,
    )
    return result
