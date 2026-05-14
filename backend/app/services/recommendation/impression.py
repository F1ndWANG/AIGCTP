from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.recommendation import RecommendationImpression


async def record_impressions(
    db: AsyncSession,
    *,
    user_id: int,
    domain: str,
    algorithm: str,
    items: list[dict[str, Any]],
    context: dict[str, Any] | None = None,
    session_id: str | None = None,
) -> list[dict[str, Any]]:
    """Attach impression IDs to ranked items and persist exposure candidates."""

    enriched: list[dict[str, Any]] = []
    for rank, item in enumerate(items, start=1):
        impression_id = uuid.uuid4().hex
        item_with_impression = {
            **item,
            "impression_id": impression_id,
            "rank": rank,
            "algorithm": algorithm,
        }
        db.add(
            RecommendationImpression(
                impression_id=impression_id,
                user_id=user_id,
                domain=item["domain"],
                item_type=item["item_type"],
                item_id=str(item["item_id"]),
                rank=rank,
                score=float(item.get("score") or 0.0),
                algorithm=algorithm,
                context=context or {},
                session_id=session_id,
            )
        )
        enriched.append(item_with_impression)
    await db.flush()
    return enriched
