from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any

from app.core.config import settings
from app.services.recommendation.embeddings import build_item_text, text_similarity
from app.services.recommendation.profile import profile_query_text

SCORE_WEIGHTS = {
    "semantic_similarity": 0.35,
    "user_affinity": 0.25,
    "context_match": 0.15,
    "popularity": 0.15,
    "freshness": 0.10,
}


def _parse_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def _freshness(metadata: dict[str, Any]) -> float:
    created_at = _parse_datetime(metadata.get("created_at"))
    if not created_at:
        return 0.35
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    age_days = max((datetime.now(timezone.utc) - created_at).total_seconds() / 86400, 0)
    return max(0.05, min(1.0, math.pow(0.5, age_days / max(settings.RECOMMENDATION_DECAY_HALF_LIFE_DAYS, 1))))


def _popularity(metadata: dict[str, Any]) -> float:
    social = (
        float(metadata.get("like_count") or 0) * 3
        + float(metadata.get("save_count") or 0) * 4
        + float(metadata.get("comment_count") or 0) * 2
        + float(metadata.get("share_count") or 0) * 4
        + min(float(metadata.get("view_count") or 0), 50) * 0.2
    )
    if social > 0:
        return max(0.0, min(0.45 + social / 80.0, 1.0))
    rating = metadata.get("rating")
    if rating is None:
        return 0.45
    try:
        return max(0.0, min(float(rating) / 5.0, 1.0))
    except (TypeError, ValueError):
        return 0.45


def _event_affinity(profile: dict[str, Any], item: dict[str, Any]) -> float:
    key = f"{item['domain']}:{item['item_type']}:{item['item_id']}"
    score = float((profile.get("event_scores") or {}).get(key, 0.0))
    if score <= -4:
        return -1.0
    return max(0.0, min(score / 8.0, 1.0))


def _context_text(context: dict[str, Any] | None) -> str:
    if not context:
        return ""
    return " ".join(str(v) for v in context.values() if v is not None)


def score_candidate(item: dict[str, Any], profile: dict[str, Any], context: dict[str, Any] | None = None) -> dict[str, float]:
    item_text = build_item_text(item)
    profile_text = profile_query_text(profile, item.get("domain"), context)
    semantic = text_similarity(item_text, profile_text)
    affinity = max(_event_affinity(profile, item), semantic * 0.7)
    context_match = text_similarity(item_text, _context_text(context))
    popularity = _popularity(item.get("metadata") or {})
    freshness = _freshness(item.get("metadata") or {})
    final_score = (
        SCORE_WEIGHTS["semantic_similarity"] * semantic
        + SCORE_WEIGHTS["user_affinity"] * affinity
        + SCORE_WEIGHTS["context_match"] * context_match
        + SCORE_WEIGHTS["popularity"] * popularity
        + SCORE_WEIGHTS["freshness"] * freshness
    )
    return {
        "semantic_similarity": semantic,
        "user_affinity": affinity,
        "context_match": context_match,
        "popularity": popularity,
        "freshness": freshness,
        "final_score": final_score,
    }


def rank_candidates(
    candidates: list[dict[str, Any]],
    *,
    profile: dict[str, Any],
    context: dict[str, Any] | None,
    limit: int,
) -> list[dict[str, Any]]:
    negative_items = profile.get("negative_items") or set()
    scored: list[dict[str, Any]] = []
    for item in candidates:
        item_key = f"{item['domain']}:{item['item_type']}:{item['item_id']}"
        if item_key in negative_items:
            continue
        scores = score_candidate(item, profile, context)
        if scores["user_affinity"] < 0:
            continue
        scored.append({**item, "_scores": scores, "_text": build_item_text(item)})

    scored.sort(key=lambda item: item["_scores"]["final_score"], reverse=True)
    selected: list[dict[str, Any]] = []
    pool = scored[: max(limit * 4, limit)]
    while pool and len(selected) < limit:
        best_idx = 0
        best_score = -10.0
        for idx, item in enumerate(pool):
            similarity_to_selected = max(
                (text_similarity(item["_text"], selected_item["_text"]) for selected_item in selected),
                default=0.0,
            )
            mmr_score = 0.75 * item["_scores"]["final_score"] - 0.25 * similarity_to_selected
            if mmr_score > best_score:
                best_idx = idx
                best_score = mmr_score
        selected.append(pool.pop(best_idx))

    return selected
