from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.feedback import RecommendationLog
from pydantic import BaseModel

router = APIRouter(prefix="/feedback", tags=["feedback"])


class FeedbackRequest(BaseModel):
    content_type: str  # travel_plan / diet / restaurant / commerce / general
    message_id: str = ""
    feedback: str      # "like" or "dislike"
    content_snapshot: dict = {}
    context: dict = {}


class FeedbackStatsResponse(BaseModel):
    content_type: str
    likes: int
    dislikes: int


@router.post("", status_code=201)
async def submit_feedback(
    payload: FeedbackRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if payload.feedback not in ("like", "dislike"):
        raise HTTPException(status_code=400, detail="Feedback must be 'like' or 'dislike'")

    log = RecommendationLog(
        user_id=current_user.id,
        content_type=payload.content_type,
        message_id=payload.message_id,
        feedback=payload.feedback,
        content_snapshot=payload.content_snapshot,
        context=payload.context,
    )
    db.add(log)
    await db.commit()
    return {"status": "ok", "id": log.id}


@router.get("/stats", response_model=list[FeedbackStatsResponse])
async def get_feedback_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(
            RecommendationLog.content_type,
            func.sum(case((RecommendationLog.feedback == "like", 1), else_=0)).label("likes"),
            func.sum(case((RecommendationLog.feedback == "dislike", 1), else_=0)).label("dislikes"),
        )
        .where(RecommendationLog.user_id == current_user.id)
        .group_by(RecommendationLog.content_type)
    )
    rows = result.all()
    return [
        FeedbackStatsResponse(content_type=row[0], likes=row[1] or 0, dislikes=row[2] or 0)
        for row in rows
    ]


@router.get("/analytics/summary")
async def get_analytics_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Aggregate analytics: total interactions, counts by content_type."""
    total_result = await db.execute(
        select(func.count(RecommendationLog.id))
        .where(RecommendationLog.user_id == current_user.id)
    )
    total = total_result.scalar() or 0

    ct_result = await db.execute(
        select(
            RecommendationLog.content_type,
            func.count(RecommendationLog.id).label("count"),
            func.sum(case((RecommendationLog.feedback == "like", 1), else_=0)).label("likes"),
        )
        .where(RecommendationLog.user_id == current_user.id)
        .group_by(RecommendationLog.content_type)
    )

    by_type = {}
    for row in ct_result.all():
        by_type[row[0]] = {
            "total": row[1],
            "likes": row[2] or 0,
            "dislikes": row[1] - (row[2] or 0),
        }

    return {
        "total_interactions": total,
        "by_content_type": by_type,
    }
