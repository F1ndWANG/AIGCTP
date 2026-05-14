from __future__ import annotations

import json
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.recommendation import RecommendationEvent
from app.services.recommendation.registry import EVENT_WEIGHTS, event_weight, is_valid_domain


def _json_safe(value: dict[str, Any] | None) -> dict[str, Any]:
    if not value:
        return {}
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


async def record_event(
    db: AsyncSession,
    *,
    user_id: int,
    domain: str,
    item_type: str,
    item_id: str | int,
    event_type: str,
    context: dict[str, Any] | None = None,
    session_id: str | None = None,
    impression_id: str | None = None,
    weight: float | None = None,
    commit: bool = True,
) -> RecommendationEvent:
    if not is_valid_domain(domain):
        raise ValueError(f"Unsupported recommendation domain: {domain}")
    if event_type not in EVENT_WEIGHTS:
        raise ValueError(f"Unsupported recommendation event_type: {event_type}")

    event = RecommendationEvent(
        user_id=user_id,
        domain=domain,
        item_type=item_type,
        item_id=str(item_id),
        event_type=event_type,
        weight=event_weight(event_type, weight),
        context=_json_safe(context),
        session_id=session_id,
        impression_id=impression_id,
    )
    db.add(event)
    if commit:
        await db.commit()
        await db.refresh(event)
    return event
