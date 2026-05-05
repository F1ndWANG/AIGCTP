from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel


class UserCreate(BaseModel):
    username: str
    password: str
    display_name: str = ""


class UserLogin(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    id: int
    username: str
    display_name: str
    avatar_url: str
    preferences: dict
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class UserPreferenceUpdate(BaseModel):
    preferences: dict[str, Any]


class UserUpdate(BaseModel):
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None


class PasswordChange(BaseModel):
    old_password: str
    new_password: str
