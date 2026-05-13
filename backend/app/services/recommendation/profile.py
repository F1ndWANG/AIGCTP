from __future__ import annotations

import math
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.recommendation import RecommendationEvent
from app.models.user import User
from app.services.recommendation.embeddings import normalize_text, tokenize


def _flatten_terms(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, dict):
        terms: list[str] = []
        for key, val in value.items():
            terms.extend(tokenize(str(key)))
            terms.extend(_flatten_terms(val))
        return terms
    if isinstance(value, (list, tuple, set)):
        terms = []
        for item in value:
            terms.extend(_flatten_terms(item))
        return terms
    return tokenize(normalize_text(value))


def _decay(created_at: datetime | None) -> float:
    if created_at is None:
        return 1.0
    now = datetime.now(timezone.utc)
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    age_days = max((now - created_at).total_seconds() / 86400, 0)
    half_life = max(settings.RECOMMENDATION_DECAY_HALF_LIFE_DAYS, 1)
    return math.pow(0.5, age_days / half_life)


async def build_user_profile(db: AsyncSession, user: User) -> dict[str, Any]:
    preferences = user.preferences or {}
    learned = preferences.get("_learned") or {}
    explicit = {k: v for k, v in preferences.items() if k != "_learned"}

    result = await db.execute(
        select(RecommendationEvent)
        .where(RecommendationEvent.user_id == user.id)
        .order_by(desc(RecommendationEvent.created_at))
        .limit(300)
    )
    events = list(result.scalars().all())

    terms: dict[str, float] = defaultdict(float)
    domain_terms: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    event_scores: dict[str, float] = defaultdict(float)
    negative_items: set[str] = set()

    for term in _flatten_terms(explicit) + _flatten_terms(learned):
        terms[term] += 1.0

    for event in events:
        decayed_weight = event.weight * _decay(event.created_at)
        item_key = f"{event.domain}:{event.item_type}:{event.item_id}"
        event_scores[item_key] += decayed_weight
        if event.event_type in {"dislike", "hide"}:
            negative_items.add(item_key)
        context_terms = _flatten_terms(event.context or {})
        for term in context_terms:
            terms[term] += max(decayed_weight, 0.2)
            domain_terms[event.domain][term] += max(decayed_weight, 0.2)

    return {
        "terms": dict(terms),
        "domain_terms": {domain: dict(values) for domain, values in domain_terms.items()},
        "event_scores": dict(event_scores),
        "negative_items": negative_items,
        "preferences": preferences,
        "event_count": len(events),
    }


def profile_query_text(profile: dict[str, Any], domain: str | None = None, context: dict[str, Any] | None = None) -> str:
    weighted_terms = profile.get("terms") or {}
    if domain:
        weighted_terms = {**weighted_terms, **((profile.get("domain_terms") or {}).get(domain) or {})}
    top_terms = sorted(weighted_terms.items(), key=lambda item: item[1], reverse=True)[:30]
    parts = [term for term, _ in top_terms]
    if context:
        parts.extend(_flatten_terms(context))
    return " ".join(parts)
