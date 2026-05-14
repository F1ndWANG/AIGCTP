from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.recommendation import (
    RecommendationEvent,
    RecommendationFeatureSnapshot,
    RecommendationImpression,
)


POSITIVE_EVENTS = {"click", "save", "select", "add_cart", "confirm_plan", "order", "like", "share", "comment"}
CONVERSION_EVENTS = {"select", "add_cart", "confirm_plan", "order"}
SOCIAL_WEIGHTS = {"like": 5, "save": 5, "comment": 4, "share": 6}


def item_key(domain: str, item_type: str, item_id: str | int) -> str:
    return f"{domain}:{item_type}:{item_id}"


async def collaborative_scores(db: AsyncSession, *, user_id: int, candidates: list[dict[str, Any]]) -> dict[str, float]:
    if not candidates:
        return {}

    user_result = await db.execute(
        select(RecommendationEvent)
        .where(
            RecommendationEvent.user_id == user_id,
            RecommendationEvent.weight > 0,
            RecommendationEvent.event_type.in_(POSITIVE_EVENTS),
        )
        .order_by(RecommendationEvent.created_at.desc())
        .limit(80)
    )
    seed_weights: dict[str, float] = defaultdict(float)
    for event in user_result.scalars().all():
        seed_weights[item_key(event.domain, event.item_type, event.item_id)] += max(float(event.weight or 0), 0.1)
    seed_keys = set(seed_weights)
    if not seed_keys:
        return {}

    candidate_keys = {item_key(item["domain"], item["item_type"], item["item_id"]) for item in candidates}
    event_result = await db.execute(
        select(RecommendationEvent)
        .where(
            RecommendationEvent.weight > 0,
            RecommendationEvent.event_type.in_(POSITIVE_EVENTS),
        )
        .order_by(RecommendationEvent.created_at.desc())
        .limit(2000)
    )
    all_positive_events = list(event_result.scalars().all())

    # Real item-to-item collaborative signal: find peer users who touched the
    # current user's positive seed items, then score candidate items by peer
    # co-occurrence strength. This is intentionally lightweight and local, but
    # it creates a true behavior graph instead of only comparing item tags.
    peer_seed_strength: dict[int, float] = defaultdict(float)
    for event in all_positive_events:
        if event.user_id == user_id:
            continue
        key = item_key(event.domain, event.item_type, event.item_id)
        if key in seed_keys:
            peer_seed_strength[event.user_id] += seed_weights[key] * max(float(event.weight or 0), 0.1)

    co_occurrence: dict[str, float] = defaultdict(float)
    for event in all_positive_events:
        peer_strength = peer_seed_strength.get(event.user_id)
        if not peer_strength:
            continue
        key = item_key(event.domain, event.item_type, event.item_id)
        if key in candidate_keys and key not in seed_keys:
            co_occurrence[key] += peer_strength * max(float(event.weight or 0), 0.1)

    if co_occurrence:
        max_score = max(co_occurrence.values()) or 1.0
        return {key: min(score / max_score, 1.0) for key, score in co_occurrence.items()}

    # Fallback for sparse data: use content overlap with the user's touched
    # items. This keeps cold-ish accounts useful before enough peers exist.
    candidate_terms: dict[str, set[str]] = {}
    touched_terms: set[str] = set()
    for item in candidates:
        metadata = item.get("metadata") or {}
        terms = {
            str(value).strip()
            for value in [metadata.get("city"), metadata.get("category")]
            if value
        }
        terms.update(str(tag).strip() for tag in metadata.get("tags") or [] if str(tag).strip())
        key = item_key(item["domain"], item["item_type"], item["item_id"])
        candidate_terms[key] = terms
        if key in seed_keys:
            touched_terms.update(terms)

    if not touched_terms:
        return {}
    scores = {}
    for key, terms in candidate_terms.items():
        overlap = len(terms & touched_terms)
        if overlap:
            scores[key] = min(0.65, overlap / max(len(terms), 1) + (0.15 if key in seed_keys else 0.0))
    return scores


async def feature_quality_scores(db: AsyncSession, *, candidates: list[dict[str, Any]]) -> dict[str, float]:
    candidate_keys = {item_key(item["domain"], item["item_type"], item["item_id"]) for item in candidates}
    if not candidate_keys:
        return {}
    result = await db.execute(select(RecommendationFeatureSnapshot))
    scores: dict[str, float] = {}
    for snapshot in result.scalars().all():
        key = item_key(snapshot.domain, snapshot.item_type, snapshot.item_id)
        if key not in candidate_keys:
            continue
        features = snapshot.features or {}
        ctr = float(features.get("ctr") or 0)
        conversion_rate = float(features.get("conversion_rate") or 0)
        social = min(float(snapshot.social_score or 0) / 50.0, 1.0)
        positive = min(float(features.get("positive_events") or 0) / 30.0, 1.0)
        negative = min(float(features.get("negative_events") or 0) / 10.0, 1.0)
        scores[key] = max(0.0, min(1.0, 0.35 * ctr + 0.35 * conversion_rate + 0.2 * social + 0.1 * positive - 0.3 * negative))
    return scores


async def refresh_feature_snapshots(db: AsyncSession, *, domain: str | None = None) -> int:
    event_filters = []
    impression_filters = []
    if domain:
        event_filters.append(RecommendationEvent.domain == domain)
        impression_filters.append(RecommendationImpression.domain == domain)

    event_result = await db.execute(select(RecommendationEvent).where(*event_filters))
    events = list(event_result.scalars().all())
    impression_result = await db.execute(select(RecommendationImpression).where(*impression_filters))
    impressions = list(impression_result.scalars().all())

    grouped_events: dict[str, list[RecommendationEvent]] = defaultdict(list)
    grouped_impressions: Counter[str] = Counter()
    for event in events:
        grouped_events[item_key(event.domain, event.item_type, event.item_id)].append(event)
    for impression in impressions:
        grouped_impressions[item_key(impression.domain, impression.item_type, impression.item_id)] += 1

    changed = 0
    for key in set(grouped_events) | set(grouped_impressions):
        item_domain, item_type, item_id = key.split(":", 2)
        counts = Counter(event.event_type for event in grouped_events.get(key, []))
        clicks = sum(counts[name] for name in ("click", "view"))
        conversions = sum(counts[name] for name in CONVERSION_EVENTS)
        social_score = sum(counts[name] * weight for name, weight in SOCIAL_WEIGHTS.items())
        impressions_count = grouped_impressions.get(key, 0)
        ctr = clicks / impressions_count if impressions_count else 0.0
        conversion_rate = conversions / impressions_count if impressions_count else 0.0
        result = await db.execute(
            select(RecommendationFeatureSnapshot).where(
                RecommendationFeatureSnapshot.domain == item_domain,
                RecommendationFeatureSnapshot.item_type == item_type,
                RecommendationFeatureSnapshot.item_id == item_id,
            )
        )
        snapshot = result.scalar_one_or_none()
        payload = {
            "event_counts": dict(counts),
            "features": {
                "ctr": round(ctr, 4),
                "conversion_rate": round(conversion_rate, 4),
                "positive_events": int(sum(max(event.weight, 0) for event in grouped_events.get(key, []))),
                "negative_events": int(abs(sum(min(event.weight, 0) for event in grouped_events.get(key, [])))),
            },
            "impressions": int(impressions_count),
            "clicks": int(clicks),
            "conversions": int(conversions),
            "social_score": float(social_score),
        }
        if snapshot is None:
            snapshot = RecommendationFeatureSnapshot(
                domain=item_domain,
                item_type=item_type,
                item_id=item_id,
                **payload,
            )
            db.add(snapshot)
        else:
            for field, value in payload.items():
                setattr(snapshot, field, value)
        changed += 1

    await db.flush()
    return changed


async def evaluation_summary(db: AsyncSession, *, user_id: int | None = None, domain: str | None = None) -> dict[str, Any]:
    impression_filters = []
    event_filters = []
    if user_id is not None:
        impression_filters.append(RecommendationImpression.user_id == user_id)
        event_filters.append(RecommendationEvent.user_id == user_id)
    if domain:
        impression_filters.append(RecommendationImpression.domain == domain)
        event_filters.append(RecommendationEvent.domain == domain)

    impressions = await db.scalar(select(func.count()).select_from(RecommendationImpression).where(*impression_filters)) or 0
    events = await db.scalar(select(func.count()).select_from(RecommendationEvent).where(*event_filters)) or 0
    clicks = await db.scalar(
        select(func.count()).select_from(RecommendationEvent).where(*event_filters, RecommendationEvent.event_type == "click")
    ) or 0
    conversions = await db.scalar(
        select(func.count())
        .select_from(RecommendationEvent)
        .where(*event_filters, RecommendationEvent.event_type.in_(CONVERSION_EVENTS))
    ) or 0
    hides = await db.scalar(
        select(func.count()).select_from(RecommendationEvent).where(*event_filters, RecommendationEvent.event_type.in_(("hide", "dislike")))
    ) or 0

    return {
        "impressions": int(impressions),
        "events": int(events),
        "clicks": int(clicks),
        "conversions": int(conversions),
        "negative_feedback": int(hides),
        "ctr": round(clicks / impressions, 4) if impressions else 0.0,
        "conversion_rate": round(conversions / impressions, 4) if impressions else 0.0,
    }
