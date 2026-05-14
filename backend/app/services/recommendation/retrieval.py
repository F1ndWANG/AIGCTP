from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.recommendation import RecommendationItem
from app.services.recommendation.catalog import item_to_candidate, load_catalog_items, rebuild_catalog
from app.services.recommendation.embeddings import build_item_text, text_similarity
from app.services.recommendation.features import collaborative_scores, feature_quality_scores, item_key
from app.services.recommendation.profile import profile_query_text


def _merge_candidate(existing: dict[str, Any], incoming: dict[str, Any], source: str) -> dict[str, Any]:
    reasons = set(existing.get("source_reasons") or [])
    reasons.add(source)
    incoming_score = float(incoming.get("_recall_score") or 0)
    existing["_recall_score"] = max(float(existing.get("_recall_score") or 0), incoming_score)
    existing["source_reasons"] = sorted(reasons)
    return existing


def _candidate_key(item: dict[str, Any]) -> str:
    return item_key(item["domain"], item["item_type"], item["item_id"])


def _business_match(candidate: dict[str, Any], context: dict[str, Any] | None) -> float:
    if not context:
        return 0.5
    metadata = candidate.get("metadata") or {}
    score = 0.0
    checks = 0
    for context_key, metadata_key in (("city", "city"), ("destination", "city"), ("category", "category"), ("cuisine", "category")):
        value = context.get(context_key)
        if value:
            checks += 1
            if str(value).lower() in str(metadata.get(metadata_key) or "").lower():
                score += 1.0
    budget = context.get("budget")
    price = metadata.get("price")
    if budget and price:
        checks += 1
        try:
            score += 1.0 if float(price) <= float(budget) else 0.25
        except (TypeError, ValueError):
            score += 0.25
    return score / checks if checks else 0.5


def _candidate_pool_limit(request_limit: int) -> int:
    configured = max(1, min(int(settings.RECOMMENDATION_MAX_CANDIDATES or 1), 500))
    return max(request_limit, configured)


def _content_recall(items: list[RecommendationItem], profile: dict[str, Any], context: dict[str, Any], limit: int) -> list[dict[str, Any]]:
    query = profile_query_text(profile, context.get("domain"), context)
    scored = []
    for item in items:
        candidate = item_to_candidate(item, recall_source="content_recall")
        score = text_similarity(build_item_text(candidate), query)
        if score > 0:
            candidate["_recall_score"] = score
            scored.append(candidate)
    scored.sort(key=lambda item: item["_recall_score"], reverse=True)
    return scored[: max(limit * 3, limit)]


def _popularity_recall(items: list[RecommendationItem], limit: int) -> list[dict[str, Any]]:
    ranked = sorted(items, key=lambda item: (item.popularity_score or 0, item.freshness_score or 0), reverse=True)
    candidates = []
    for item in ranked[: max(limit * 3, limit)]:
        candidate = item_to_candidate(item, recall_source="popularity_recall")
        candidate["_recall_score"] = float(item.popularity_score or 0)
        candidates.append(candidate)
    return candidates


def _session_recall(items: list[RecommendationItem], profile: dict[str, Any], context: dict[str, Any], limit: int) -> list[dict[str, Any]]:
    text = " ".join(str(value) for value in context.values() if value)
    if not text:
        text = profile_query_text(profile, None, context)
    if not text:
        return []
    scored = []
    for item in items:
        candidate = item_to_candidate(item, recall_source="session_recall")
        score = text_similarity(build_item_text(candidate), text)
        if score > 0.05:
            candidate["_recall_score"] = score
            scored.append(candidate)
    scored.sort(key=lambda item: item["_recall_score"], reverse=True)
    return scored[: max(limit * 2, limit)]


def _cross_domain_recall(items: list[RecommendationItem], context: dict[str, Any], limit: int) -> list[dict[str, Any]]:
    destination = context.get("destination") or context.get("city")
    if not destination:
        return []
    scored = []
    for item in items:
        candidate = item_to_candidate(item, recall_source="cross_domain_recall")
        metadata = candidate.get("metadata") or {}
        if str(destination).lower() in str(metadata.get("city") or "").lower():
            candidate["_recall_score"] = 0.75
            scored.append(candidate)
    return scored[: max(limit * 2, limit)]


async def retrieve_candidates(
    db: AsyncSession,
    *,
    user_id: int,
    domain: str,
    profile: dict[str, Any],
    context: dict[str, Any] | None,
    limit: int,
) -> list[dict[str, Any]]:
    context = {**(context or {}), "domain": domain}
    items = await load_catalog_items(db, user_id=user_id, domain=domain, limit=limit)
    if not items:
        await rebuild_catalog(db, user_id=user_id, domain=None if domain == "home" else domain)
        items = await load_catalog_items(db, user_id=user_id, domain=domain, limit=limit)

    recalls = [
        *_content_recall(items, profile, context, limit),
        *_popularity_recall(items, limit),
        *_session_recall(items, profile, context, limit),
        *_cross_domain_recall(items, context, limit),
    ]

    merged: dict[str, dict[str, Any]] = {}
    for candidate in recalls:
        key = _candidate_key(candidate)
        source = (candidate.get("source_reasons") or ["catalog"])[0]
        if key in merged:
            _merge_candidate(merged[key], candidate, source)
        else:
            candidate["business_constraint_score"] = _business_match(candidate, context)
            merged[key] = candidate

    collab = await collaborative_scores(db, user_id=user_id, candidates=list(merged.values()))
    for key, score in collab.items():
        if key in merged:
            merged[key]["collaborative_score"] = score
            reasons = set(merged[key].get("source_reasons") or [])
            reasons.add("collaborative_recall")
            merged[key]["source_reasons"] = sorted(reasons)

    quality = await feature_quality_scores(db, candidates=list(merged.values()))
    for key, score in quality.items():
        if key in merged:
            merged[key]["feature_quality_score"] = score
            reasons = set(merged[key].get("source_reasons") or [])
            reasons.add("feature_quality")
            merged[key]["source_reasons"] = sorted(reasons)

    candidates = sorted(
        merged.values(),
        key=lambda item: (
            float(item.get("_recall_score") or 0),
            float((item.get("metadata") or {}).get("popularity_score") or 0),
            float((item.get("metadata") or {}).get("freshness_score") or 0),
        ),
        reverse=True,
    )
    return candidates[: _candidate_pool_limit(limit)]
