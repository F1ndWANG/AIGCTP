from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


class RestaurantRecommendationResponse(BaseModel):
    id: int
    session_id: Optional[str] = None
    city: str = ""
    query: str = ""
    response: str = ""
    restaurants: list[dict[str, Any]] = []
    selected_restaurant: Optional[dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RestaurantSelectionRequest(BaseModel):
    restaurant: dict[str, Any]
