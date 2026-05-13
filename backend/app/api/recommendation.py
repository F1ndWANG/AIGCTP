from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.recommendation import (
    RecommendationEventRequest,
    RecommendationFeedbackRequest,
    RecommendationFeedResponse,
    RecommendationFeedItem,
    RecommendationProfileResponse,
    RefreshEmbeddingsRequest,
    VALID_RECOMMENDATION_DOMAINS,
)
from app.services.recommendation import recommendation_service

router = APIRouter(prefix="/recommend", tags=["recommendation"])


@router.post("/events", status_code=status.HTTP_201_CREATED)
async def track_recommendation_event(
    payload: RecommendationEventRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    event = await recommendation_service.track(
        db,
        user_id=current_user.id,
        domain=payload.domain,
        item_type=payload.item_type,
        item_id=payload.item_id,
        event_type=payload.event_type,
        context=payload.context,
        session_id=payload.session_id,
        weight=payload.weight,
    )
    return {"id": event.id, "status": "recorded"}


@router.get("/feed", response_model=RecommendationFeedResponse)
async def get_recommendation_feed(
    domain: str = Query("home"),
    limit: int = Query(12, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if domain not in VALID_RECOMMENDATION_DOMAINS:
        raise HTTPException(status_code=422, detail="invalid recommendation domain")
    items = await recommendation_service.recommend(
        db,
        user=current_user,
        domain=domain,
        limit=limit,
        context={"entry": "feed"},
    )
    return RecommendationFeedResponse(
        items=[RecommendationFeedItem(**item) for item in items],
        total=len(items),
        algorithm=recommendation_service.algorithm,
    )


@router.get("/profile", response_model=RecommendationProfileResponse)
async def get_recommendation_profile(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return RecommendationProfileResponse(**await recommendation_service.profile_insights(db, user=current_user))


@router.post("/refresh-embeddings")
async def refresh_recommendation_embeddings(
    payload: RefreshEmbeddingsRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    count = await recommendation_service.refresh_embeddings(
        db,
        user=current_user,
        domain=payload.domain,
        item_ids=payload.item_ids,
    )
    return {"status": "ok", "refreshed": count, "model": "local-token-vector"}


@router.post("/feedback", status_code=status.HTTP_201_CREATED)
async def recommendation_feedback(
    payload: RecommendationFeedbackRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    event = await recommendation_service.track(
        db,
        user_id=current_user.id,
        domain=payload.domain,
        item_type=payload.item_type,
        item_id=payload.item_id,
        event_type=payload.feedback,
        context=payload.context,
        session_id=payload.session_id,
    )
    return {"id": event.id, "status": "recorded"}
