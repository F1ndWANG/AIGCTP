from datetime import datetime, date
from typing import Optional, Any
from pydantic import BaseModel


class TravelPlanRequest(BaseModel):
    destination: str
    days: int = 3
    start_date: Optional[date] = None
    budget: Optional[float] = None
    people_count: int = 1
    preferences: dict[str, Any] = {}


class TravelPlanAdjustment(BaseModel):
    plan_id: int
    instruction: str  # e.g. "第二天太赶了", "预算控制在2000以内"


class TravelPlanResponse(BaseModel):
    id: int
    destination: str
    days: int
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    budget: Optional[float] = None
    people_count: int
    preferences: dict
    itinerary: Optional[dict]
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TravelPlanListItem(BaseModel):
    id: int
    destination: str
    days: int
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatSessionListItem(BaseModel):
    session_id: str
    title: str
    message_count: int
    last_preview: str
    updated_at: datetime

    model_config = {"from_attributes": True}


class ChatSessionDetailResponse(BaseModel):
    session_id: str
    title: str
    messages: list
    context: dict
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    message: str
    travel_plan_id: Optional[int] = None  # for adjustments on existing plan


class ChatResponse(BaseModel):
    session_id: str
    message: str
    travel_plan: Optional[TravelPlanResponse] = None
