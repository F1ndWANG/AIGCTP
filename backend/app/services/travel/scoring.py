from __future__ import annotations

from typing import Any

from app.services.recommendation.embeddings import text_similarity
from app.services.travel.constraints import normalize_name


def _text(value: dict[str, Any]) -> str:
    parts = []
    for key in ("name", "title", "description", "reason", "address", "category", "type"):
        if value.get(key):
            parts.append(str(value[key]))
    tags = value.get("tags")
    if isinstance(tags, list):
        parts.extend(str(tag) for tag in tags)
    return " ".join(parts)


def _rating(value: dict[str, Any]) -> float:
    rating = value.get("rating") or value.get("score") or 0
    try:
        return max(0.0, min(float(rating) / 5.0, 1.0))
    except (TypeError, ValueError):
        return 0.45


def score_poi(poi: dict[str, Any], constraints: dict[str, Any], destination: str) -> float:
    name = str(poi.get("name") or "")
    normalized = normalize_name(name)
    must_visit = {normalize_name(item) for item in constraints.get("must_visit") or []}
    avoid = {normalize_name(item) for item in constraints.get("avoid_pois") or []}
    if any(item and (item in normalized or normalized in item) for item in avoid):
        return -1.0
    score = 0.45 + 0.25 * _rating(poi)
    if any(item and (item in normalized or normalized in item) for item in must_visit):
        score += 0.45
    query = " ".join([destination, *(constraints.get("must_visit") or []), str(constraints.get("pace") or "")])
    score += 0.2 * text_similarity(_text(poi), query)
    return min(score, 1.0)


def score_restaurant(restaurant: dict[str, Any], constraints: dict[str, Any]) -> float:
    score = 0.45 + 0.25 * _rating(restaurant)
    cuisine = constraints.get("cuisine")
    if cuisine and cuisine in _text(restaurant):
        score += 0.25
    return min(score, 1.0)


def score_product(product: dict[str, Any], constraints: dict[str, Any], destination: str) -> float:
    query = " ".join([destination, "旅行 便携 出行", str(constraints.get("pace") or "")])
    return min(0.35 + 0.45 * text_similarity(_text(product), query) + 0.2 * _rating(product), 1.0)


def score_hotel(hotel: dict[str, Any], constraints: dict[str, Any], destination: str) -> float:
    query = " ".join([destination, "地铁 商圈 便利 可取消"])
    return min(0.45 + 0.35 * text_similarity(_text(hotel), query) + 0.2 * _rating(hotel), 1.0)
