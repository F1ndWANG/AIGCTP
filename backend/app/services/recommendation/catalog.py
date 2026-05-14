from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import and_, desc, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.commerce import Product
from app.models.diet import DietPlan
from app.models.recommendation import RecommendationItem
from app.models.restaurant import RestaurantRecommendation
from app.models.share import TravelNote
from app.models.travel import TravelPlan
from app.services.recommendation.registry import CATALOG_DOMAIN_ORDER


def _first_image(value: Any) -> str | None:
    if isinstance(value, list) and value:
        return str(value[0])
    if isinstance(value, str) and value:
        return value
    return None


def _tags(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if item is not None and str(item).strip()][:20]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _freshness(created_at: datetime | None) -> float:
    if not created_at:
        return 0.35
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    age_days = max((datetime.now(timezone.utc) - created_at).total_seconds() / 86400, 0)
    return max(0.05, min(1.0, math.pow(0.5, age_days / 30)))


def _travel_title(plan: TravelPlan) -> str:
    preferences = plan.preferences or {}
    return str(preferences.get("theme") or preferences.get("title") or f"{plan.destination}{plan.days}日行程")


def _itinerary_text(plan: TravelPlan) -> str:
    itinerary = plan.itinerary or {}
    parts: list[str] = []
    for day in itinerary.get("day_by_day", []) or []:
        if day.get("theme"):
            parts.append(str(day["theme"]))
        for activity in day.get("activities", []) or []:
            parts.extend(str(activity.get(key) or "") for key in ("poi", "description", "tips"))
        for meal in day.get("meals", []) or []:
            parts.extend(str(meal.get(key) or "") for key in ("restaurant", "recommendation", "description"))
    return " ".join(part for part in parts if part).strip()


def _note_popularity(note: TravelNote) -> float:
    social = (
        (note.like_count or 0) * 3
        + (note.save_count or 0) * 4
        + (note.comment_count or 0) * 2
        + (note.share_count or 0) * 4
        + min(note.view_count or 0, 100) * 0.2
    )
    return max(0.0, min(1.0, 0.35 + social / 120))


def _product_payload(product: Product) -> dict[str, Any]:
    return {
        "domain": "commerce",
        "item_type": "product",
        "source_id": str(product.id),
        "source_user_id": None,
        "title": product.name,
        "description": product.description or "",
        "tags": _tags(product.tags),
        "city": None,
        "category": product.category.name if product.category else None,
        "price": float(product.price),
        "rating": float(product.rating or 0),
        "popularity_score": max(0.0, min(float(product.rating or 0) / 5.0, 1.0)),
        "freshness_score": _freshness(product.created_at),
        "item_metadata": {
            "unit": product.unit,
            "stock": product.stock,
            "source": product.source,
            "created_at": product.created_at.isoformat() if product.created_at else None,
        },
        "image_url": _first_image(product.image_urls),
        "url": f"/products/{product.id}",
        "active": product.status == "active",
    }


def _travel_plan_payload(plan: TravelPlan) -> dict[str, Any]:
    preferences = plan.preferences or {}
    tags = _tags(preferences.get("tags"))
    if preferences.get("theme"):
        tags.append(str(preferences["theme"]))
    return {
        "domain": "travel",
        "item_type": "travel_plan",
        "source_id": str(plan.id),
        "source_user_id": plan.user_id,
        "title": _travel_title(plan),
        "description": str(preferences.get("summary") or preferences.get("notes") or _itinerary_text(plan)),
        "tags": tags,
        "city": plan.destination,
        "category": "confirmed" if plan.status == "confirmed" else "draft",
        "price": float(plan.budget) if plan.budget is not None else None,
        "rating": None,
        "popularity_score": 0.55 if plan.status == "confirmed" else 0.4,
        "freshness_score": _freshness(plan.updated_at or plan.created_at),
        "item_metadata": {
            "days": plan.days,
            "status": plan.status,
            "preferences": preferences,
            "created_at": plan.created_at.isoformat() if plan.created_at else None,
        },
        "image_url": None,
        "url": f"/travel/{plan.id}",
        "active": True,
    }


def _travel_note_payload(note: TravelNote) -> dict[str, Any]:
    return {
        "domain": "travel",
        "item_type": "travel_note",
        "source_id": str(note.id),
        "source_user_id": note.author_id,
        "title": note.title,
        "description": note.content[:1000],
        "tags": _tags(note.tags),
        "city": note.destination,
        "category": "travel_note",
        "price": None,
        "rating": None,
        "popularity_score": _note_popularity(note),
        "freshness_score": _freshness(note.updated_at or note.created_at),
        "item_metadata": {
            "visibility": note.visibility,
            "is_public": note.visibility == "public",
            "is_featured": bool(note.is_featured),
            "view_count": note.view_count or 0,
            "like_count": note.like_count or 0,
            "save_count": note.save_count or 0,
            "comment_count": note.comment_count or 0,
            "share_count": note.share_count or 0,
            "author_id": note.author_id,
            "created_at": note.created_at.isoformat() if note.created_at else None,
        },
        "image_url": _first_image(note.images),
        "url": f"/shares/{note.id}",
        "active": note.visibility == "public",
    }


def _diet_plan_payload(plan: DietPlan) -> dict[str, Any]:
    return {
        "domain": "diet",
        "item_type": "diet_plan",
        "source_id": str(plan.id),
        "source_user_id": plan.user_id,
        "title": plan.title or f"{plan.duration_days}天饮食计划",
        "description": " ".join(plan.tips or []) if isinstance(plan.tips, list) else "",
        "tags": _tags(plan.tips),
        "city": None,
        "category": plan.status,
        "price": None,
        "rating": None,
        "popularity_score": 0.5 if plan.status == "active" else 0.35,
        "freshness_score": _freshness(plan.updated_at or plan.created_at),
        "item_metadata": {
            "duration_days": plan.duration_days,
            "status": plan.status,
            "nutrition": plan.total_nutrition or {},
            "created_at": plan.created_at.isoformat() if plan.created_at else None,
        },
        "image_url": None,
        "url": "/diet",
        "active": True,
    }


def _restaurant_payload(source_id: int, user_id: int, recommendation: RestaurantRecommendation, restaurant: dict[str, Any]) -> dict[str, Any]:
    name = restaurant.get("name") or restaurant.get("title") or "餐厅推荐"
    city = restaurant.get("city") or restaurant.get("location_city") or recommendation.city
    cuisine = restaurant.get("cuisine") or restaurant.get("category") or restaurant.get("type")
    rating = restaurant.get("rating") or restaurant.get("score") or 0
    avg_price = restaurant.get("price") or restaurant.get("avg_price")
    item_id = restaurant.get("id") or restaurant.get("poi_id") or f"{source_id}:{name}"
    return {
        "domain": "restaurant",
        "item_type": "restaurant",
        "source_id": str(item_id),
        "source_user_id": user_id,
        "title": str(name),
        "description": restaurant.get("reason") or restaurant.get("description") or restaurant.get("address") or "",
        "tags": _tags([cuisine, city, restaurant.get("address")]),
        "city": city,
        "category": cuisine,
        "price": float(avg_price) if isinstance(avg_price, (int, float)) else None,
        "rating": float(rating or 0),
        "popularity_score": max(0.0, min(float(rating or 0) / 5.0, 1.0)) if rating else 0.45,
        "freshness_score": _freshness(recommendation.created_at),
        "item_metadata": {
            "recommendation_id": source_id,
            "query": recommendation.query,
            "raw": restaurant,
            "created_at": recommendation.created_at.isoformat() if recommendation.created_at else None,
        },
        "image_url": _first_image(restaurant.get("photos") or restaurant.get("image_url")),
        "url": "/restaurants",
        "active": True,
    }


async def _upsert_item(db: AsyncSession, payload: dict[str, Any]) -> RecommendationItem:
    result = await db.execute(
        select(RecommendationItem).where(
            RecommendationItem.domain == payload["domain"],
            RecommendationItem.item_type == payload["item_type"],
            RecommendationItem.source_id == payload["source_id"],
        )
    )
    item = result.scalar_one_or_none()
    if item is None:
        item = RecommendationItem(**payload)
        db.add(item)
        return item
    for key, value in payload.items():
        setattr(item, key, value)
    return item


async def sync_product_item(db: AsyncSession, product: Product) -> RecommendationItem:
    item = await _upsert_item(db, _product_payload(product))
    await db.flush()
    return item


async def sync_travel_plan_item(db: AsyncSession, plan: TravelPlan) -> RecommendationItem:
    item = await _upsert_item(db, _travel_plan_payload(plan))
    await db.flush()
    return item


async def sync_travel_note_item(db: AsyncSession, note: TravelNote) -> RecommendationItem:
    item = await _upsert_item(db, _travel_note_payload(note))
    await db.flush()
    return item


async def sync_diet_plan_item(db: AsyncSession, plan: DietPlan) -> RecommendationItem:
    item = await _upsert_item(db, _diet_plan_payload(plan))
    await db.flush()
    return item


async def sync_restaurant_recommendation_items(db: AsyncSession, recommendation: RestaurantRecommendation) -> int:
    count = 0
    for restaurant in recommendation.restaurants or []:
        await _upsert_item(db, _restaurant_payload(recommendation.id, recommendation.user_id, recommendation, restaurant))
        count += 1
    await db.flush()
    return count


async def rebuild_catalog(db: AsyncSession, *, user_id: int | None = None, domain: str | None = None, limit: int = 500) -> int:
    """Refresh the normalized item catalog from current domain tables."""

    domains = [domain] if domain else list(CATALOG_DOMAIN_ORDER)
    count = 0

    if "commerce" in domains:
        result = await db.execute(
            select(Product)
            .where(Product.status == "active")
            .options(selectinload(Product.category))
            .order_by(desc(Product.updated_at), desc(Product.created_at))
            .limit(limit)
        )
        for product in result.scalars().unique().all():
            await _upsert_item(db, _product_payload(product))
            count += 1

    if "travel" in domains:
        plan_query = select(TravelPlan).order_by(desc(TravelPlan.updated_at), desc(TravelPlan.created_at)).limit(limit)
        if user_id is not None:
            plan_query = plan_query.where(TravelPlan.user_id == user_id)
        plan_result = await db.execute(plan_query)
        for plan in plan_result.scalars().all():
            await _upsert_item(db, _travel_plan_payload(plan))
            count += 1

        note_result = await db.execute(
            select(TravelNote)
            .where(TravelNote.visibility == "public")
            .order_by(desc(TravelNote.is_featured), desc(TravelNote.updated_at), desc(TravelNote.created_at))
            .limit(limit)
        )
        for note in note_result.scalars().all():
            await _upsert_item(db, _travel_note_payload(note))
            count += 1

    if "restaurant" in domains:
        restaurant_query = select(RestaurantRecommendation).order_by(desc(RestaurantRecommendation.created_at)).limit(limit)
        if user_id is not None:
            restaurant_query = restaurant_query.where(RestaurantRecommendation.user_id == user_id)
        restaurant_result = await db.execute(restaurant_query)
        for recommendation in restaurant_result.scalars().all():
            for restaurant in recommendation.restaurants or []:
                await _upsert_item(db, _restaurant_payload(recommendation.id, recommendation.user_id, recommendation, restaurant))
                count += 1

    if "diet" in domains:
        diet_query = select(DietPlan).order_by(desc(DietPlan.updated_at), desc(DietPlan.created_at)).limit(limit)
        if user_id is not None:
            diet_query = diet_query.where(DietPlan.user_id == user_id)
        diet_result = await db.execute(diet_query)
        for plan in diet_result.scalars().all():
            await _upsert_item(db, _diet_plan_payload(plan))
            count += 1

    await db.flush()
    return count


def item_to_candidate(item: RecommendationItem, *, recall_source: str = "catalog") -> dict[str, Any]:
    return {
        "domain": item.domain,
        "item_type": item.item_type,
        "item_id": item.source_id,
        "title": item.title,
        "subtitle": _subtitle(item),
        "description": item.description,
        "image_url": item.image_url,
        "url": item.url,
        "metadata": {
            **(item.item_metadata or {}),
            "tags": item.tags or [],
            "city": item.city,
            "category": item.category,
            "price": item.price,
            "rating": item.rating,
            "popularity_score": item.popularity_score,
            "freshness_score": item.freshness_score,
            "source_user_id": item.source_user_id,
        },
        "source_reasons": [recall_source],
    }


def _subtitle(item: RecommendationItem) -> str | None:
    if item.domain == "commerce" and item.price is not None:
        return f"¥{item.price:.1f}"
    parts = [item.city, item.category]
    return " · ".join(part for part in parts if part) or None


async def load_catalog_items(
    db: AsyncSession,
    *,
    user_id: int,
    domain: str,
    limit: int,
) -> list[RecommendationItem]:
    filters = [RecommendationItem.active.is_(True)]
    if domain != "home":
        filters.append(RecommendationItem.domain == domain)
    filters.append(
        or_(
            RecommendationItem.source_user_id.is_(None),
            RecommendationItem.source_user_id == user_id,
            and_(
                RecommendationItem.domain == "travel",
                RecommendationItem.item_type == "travel_note",
                RecommendationItem.category == "travel_note",
            ),
        )
    )
    result = await db.execute(
        select(RecommendationItem)
        .where(*filters)
        .order_by(desc(RecommendationItem.popularity_score), desc(RecommendationItem.freshness_score), desc(RecommendationItem.updated_at))
        .limit(max(limit * 8, 64))
    )
    return list(result.scalars().all())
