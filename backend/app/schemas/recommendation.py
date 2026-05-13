from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


VALID_RECOMMENDATION_DOMAINS = {"home", "commerce", "restaurant", "travel", "diet"}
VALID_RECOMMENDATION_EVENTS = {
    "view",
    "click",
    "chat_mention",
    "save",
    "select",
    "add_cart",
    "confirm_plan",
    "order",
    "like",
    "dislike",
    "hide",
    "share",
    "comment",
}


class RecommendationEventRequest(BaseModel):
    domain: str
    item_type: str = Field(min_length=1, max_length=30)
    item_id: str | int
    event_type: str
    weight: float | None = None
    context: dict[str, Any] = Field(default_factory=dict)
    session_id: str | None = Field(default=None, max_length=100)

    @field_validator("domain")
    @classmethod
    def validate_domain(cls, value: str) -> str:
        if value not in VALID_RECOMMENDATION_DOMAINS:
            raise ValueError("invalid recommendation domain")
        return value

    @field_validator("event_type")
    @classmethod
    def validate_event_type(cls, value: str) -> str:
        if value not in VALID_RECOMMENDATION_EVENTS:
            raise ValueError("invalid recommendation event_type")
        return value


class RecommendationFeedbackRequest(BaseModel):
    domain: str
    item_type: str = Field(min_length=1, max_length=30)
    item_id: str | int
    feedback: Literal["like", "dislike", "hide", "save", "select"]
    context: dict[str, Any] = Field(default_factory=dict)
    session_id: str | None = Field(default=None, max_length=100)

    @field_validator("domain")
    @classmethod
    def validate_domain(cls, value: str) -> str:
        if value not in VALID_RECOMMENDATION_DOMAINS:
            raise ValueError("invalid recommendation domain")
        return value


class RecommendationFeedItem(BaseModel):
    domain: str
    item_type: str
    item_id: str
    title: str
    subtitle: str | None = None
    description: str | None = None
    image_url: str | None = None
    url: str | None = None
    score: float
    reason: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class RecommendationFeedResponse(BaseModel):
    items: list[RecommendationFeedItem]
    total: int
    algorithm: str = "hybrid_v1"


class RecommendationProfileTerm(BaseModel):
    term: str
    weight: float


class RecommendationProfileResponse(BaseModel):
    algorithm: str = "hybrid_v1"
    event_count: int
    top_terms: list[RecommendationProfileTerm]
    domain_terms: dict[str, list[RecommendationProfileTerm]]
    negative_item_count: int
    preferences: dict[str, Any] = Field(default_factory=dict)


class RefreshEmbeddingsRequest(BaseModel):
    domain: str | None = None
    item_ids: list[str] | None = None

    @field_validator("domain")
    @classmethod
    def validate_optional_domain(cls, value: str | None) -> str | None:
        if value is not None and value not in VALID_RECOMMENDATION_DOMAINS:
            raise ValueError("invalid recommendation domain")
        return value
