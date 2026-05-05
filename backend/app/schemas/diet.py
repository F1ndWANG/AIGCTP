from datetime import datetime, date
from typing import Optional, Any
from pydantic import BaseModel


class HealthProfileRequest(BaseModel):
    height: Optional[float] = None
    weight: Optional[float] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    allergies: list[str] = []
    chronic_conditions: list[str] = []
    diet_goals: list[str] = []
    dietary_restrictions: list[str] = []


class HealthProfileResponse(BaseModel):
    id: int
    height: Optional[float] = None
    weight: Optional[float] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    allergies: list[str]
    chronic_conditions: list[str]
    diet_goals: list[str]
    dietary_restrictions: list[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MealRecordRequest(BaseModel):
    date: date
    meal_type: str  # breakfast / lunch / dinner / snack
    foods: list[dict[str, Any]] = []
    total_nutrition: Optional[dict[str, Any]] = None
    notes: str = ""


class MealRecordResponse(BaseModel):
    id: int
    user_id: int
    date: date
    meal_type: str
    foods: list[dict[str, Any]]
    total_nutrition: Optional[dict[str, Any]] = None
    notes: str
    created_at: datetime

    model_config = {"from_attributes": True}


class MealRecordListResponse(BaseModel):
    records: list[MealRecordResponse]
    total_calories: float = 0
    total_protein: float = 0
    total_carbs: float = 0
    total_fat: float = 0


class DietPlanResponse(BaseModel):
    id: int
    title: str
    duration_days: int
    meals: Optional[dict] = None
    total_nutrition: Optional[dict] = None
    tips: list[str]
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DietPlanListItem(BaseModel):
    id: int
    title: str
    duration_days: int
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}
