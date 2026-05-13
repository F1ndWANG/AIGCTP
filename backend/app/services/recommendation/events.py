from __future__ import annotations

import json
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.recommendation import RecommendationEvent


EVENT_WEIGHTS: dict[str, float] = {
    "view": 1.0,
    "click": 2.0,
    "chat_mention": 2.0,
    "save": 3.0,
    "select": 4.0,
    "add_cart": 4.0,
    "confirm_plan": 5.0,
    "order": 6.0,
    "like": 5.0,
    "dislike": -5.0,
    "hide": -4.0,
    "share": 4.0,
    "comment": 3.0,
}

VALID_DOMAINS = {"home", "commerce", "restaurant", "travel", "diet"}


def _json_safe(value: dict[str, Any] | None) -> dict[str, Any]:
    if not value:
        return {}
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def event_weight(event_type: str, override: float | None = None) -> float:
    if override is not None:
        return float(override)
    return EVENT_WEIGHTS[event_type]


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
    weight: float | None = None,
    commit: bool = True,
) -> RecommendationEvent:
    if domain not in VALID_DOMAINS:
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
    )
    db.add(event)
    if commit:
        await db.commit()
        await db.refresh(event)
    return event
