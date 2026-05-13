from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class TravelNoteAuthor(BaseModel):
    id: int
    username: str
    display_name: str
    avatar_url: str | None = None


class TravelNoteCreate(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    content: str = Field(min_length=5, max_length=8000)
    destination: str = Field(default="", max_length=100)
    tags: list[str] = Field(default_factory=list)
    images: list[str] = Field(default_factory=list)
    travel_plan_id: int | None = None
    visibility: Literal["public", "private"] = "public"


class TravelNoteUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=200)
    content: str | None = Field(default=None, min_length=5, max_length=8000)
    destination: str | None = Field(default=None, max_length=100)
    tags: list[str] | None = None
    images: list[str] | None = None
    visibility: Literal["public", "private"] | None = None


class TravelNoteInteractionRequest(BaseModel):
    interaction_type: Literal["view", "like", "save", "share"]
    active: bool = True


class TravelNoteCommentCreate(BaseModel):
    content: str = Field(min_length=1, max_length=1000)


class TravelNoteCommentResponse(BaseModel):
    id: int
    content: str
    author: TravelNoteAuthor
    created_at: datetime


class TravelNoteResponse(BaseModel):
    id: int
    title: str
    content: str
    destination: str = ""
    tags: list[str] = []
    images: list[str] = []
    visibility: str
    is_featured: bool = False
    view_count: int = 0
    like_count: int = 0
    save_count: int = 0
    comment_count: int = 0
    share_count: int = 0
    created_at: datetime
    updated_at: datetime
    author: TravelNoteAuthor
    travel_plan_id: int | None = None
    viewer_interactions: dict[str, bool] = Field(default_factory=dict)
    comments: list[TravelNoteCommentResponse] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
