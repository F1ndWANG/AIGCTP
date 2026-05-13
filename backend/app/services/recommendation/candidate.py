from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.commerce import Product
from app.models.diet import DietPlan
from app.models.restaurant import RestaurantRecommendation
from app.models.share import TravelNote
from app.models.travel import TravelPlan


def _first_image(value: Any) -> str | None:
    if isinstance(value, list) and value:
        return value[0]
    if isinstance(value, str) and value:
        return value
    return None


def _to_iso(value: Any) -> str | None:
    if isinstance(value, datetime):
        return value.isoformat()
    return None


def product_candidate(product: Product) -> dict[str, Any]:
    return {
        "domain": "commerce",
        "item_type": "product",
        "item_id": str(product.id),
        "title": product.name,
        "subtitle": f"¥{float(product.price):.1f}",
        "description": product.description,
        "image_url": _first_image(product.image_urls),
        "url": f"/products/{product.id}",
        "metadata": {
            "price": float(product.price),
            "rating": float(product.rating or 0),
            "tags": product.tags or [],
            "category": product.category.name if product.category else None,
            "created_at": _to_iso(product.created_at),
        },
    }


def travel_candidate(plan: TravelPlan) -> dict[str, Any]:
    preferences = plan.preferences or {}
    title = preferences.get("theme") or preferences.get("title") or f"{plan.destination}{plan.days}日行程"
    return {
        "domain": "travel",
        "item_type": "travel_plan",
        "item_id": str(plan.id),
        "title": title,
        "subtitle": f"{plan.destination} · {plan.days} 天",
        "description": preferences.get("summary") or preferences.get("notes"),
        "image_url": None,
        "url": f"/travel/{plan.id}",
        "metadata": {
            "city": plan.destination,
            "status": plan.status,
            "preferences": preferences,
            "created_at": _to_iso(plan.created_at),
        },
    }


def travel_note_candidate(note: TravelNote) -> dict[str, Any]:
    return {
        "domain": "travel",
        "item_type": "travel_note",
        "item_id": str(note.id),
        "title": note.title,
        "subtitle": f"{note.destination or '旅行笔记'} · {note.author.display_name or note.author.username if note.author else '用户分享'}",
        "description": note.content[:240],
        "image_url": _first_image(note.images),
        "url": f"/shares/{note.id}",
        "metadata": {
            "city": note.destination,
            "tags": note.tags or [],
            "created_at": _to_iso(note.created_at),
            "view_count": note.view_count or 0,
            "like_count": note.like_count or 0,
            "save_count": note.save_count or 0,
            "comment_count": note.comment_count or 0,
            "share_count": note.share_count or 0,
            "author_id": note.author_id,
        },
    }


def diet_candidate(plan: DietPlan) -> dict[str, Any]:
    return {
        "domain": "diet",
        "item_type": "diet_plan",
        "item_id": str(plan.id),
        "title": plan.title,
        "subtitle": f"{plan.duration_days} 天饮食计划",
        "description": " ".join(plan.tips or []) if isinstance(plan.tips, list) else None,
        "image_url": None,
        "url": "/diet",
        "metadata": {
            "status": plan.status,
            "nutrition": plan.total_nutrition or {},
            "created_at": _to_iso(plan.created_at),
        },
    }


def restaurant_candidate(source_id: int, restaurant: dict[str, Any]) -> dict[str, Any]:
    name = restaurant.get("name") or restaurant.get("title") or "餐厅推荐"
    city = restaurant.get("city") or restaurant.get("location_city")
    cuisine = restaurant.get("cuisine") or restaurant.get("category") or restaurant.get("type")
    rating = restaurant.get("rating") or restaurant.get("score") or 0
    return {
        "domain": "restaurant",
        "item_type": "restaurant",
        "item_id": str(restaurant.get("id") or restaurant.get("poi_id") or f"{source_id}:{name}"),
        "title": name,
        "subtitle": " · ".join(str(v) for v in [city, cuisine] if v),
        "description": restaurant.get("reason") or restaurant.get("description") or restaurant.get("address"),
        "image_url": _first_image(restaurant.get("photos") or restaurant.get("image_url")),
        "url": "/restaurants",
        "metadata": {
            "city": city,
            "cuisine": cuisine,
            "rating": float(rating or 0),
            "price": restaurant.get("price") or restaurant.get("avg_price"),
            "raw": restaurant,
        },
    }


async def collect_domain_candidates(
    db: AsyncSession,
    *,
    user_id: int,
    domain: str,
    limit: int,
) -> list[dict[str, Any]]:
    if domain == "home":
        candidates: list[dict[str, Any]] = []
        for subdomain in ("travel", "restaurant", "commerce", "diet"):
            candidates.extend(await collect_domain_candidates(db, user_id=user_id, domain=subdomain, limit=max(4, limit // 2)))
        return candidates

    if domain == "commerce":
        result = await db.execute(
            select(Product)
            .where(Product.status == "active")
            .options(selectinload(Product.category))
            .order_by(desc(Product.rating), desc(Product.created_at))
            .limit(max(limit * 4, 24))
        )
        return [product_candidate(product) for product in result.scalars().unique().all()]

    if domain == "travel":
        plan_result = await db.execute(
            select(TravelPlan)
            .where(TravelPlan.user_id == user_id)
            .order_by(desc(TravelPlan.updated_at), desc(TravelPlan.created_at))
            .limit(max(limit * 3, 18))
        )
        note_result = await db.execute(
            select(TravelNote)
            .where(TravelNote.visibility == "public")
            .options(selectinload(TravelNote.author))
            .order_by(desc(TravelNote.is_featured), desc(TravelNote.like_count), desc(TravelNote.created_at))
            .limit(max(limit * 3, 18))
        )
        return [travel_candidate(plan) for plan in plan_result.scalars().all()] + [
            travel_note_candidate(note) for note in note_result.scalars().all()
        ]

    if domain == "diet":
        result = await db.execute(
            select(DietPlan)
            .where(DietPlan.user_id == user_id)
            .order_by(desc(DietPlan.updated_at), desc(DietPlan.created_at))
            .limit(max(limit * 3, 18))
        )
        return [diet_candidate(plan) for plan in result.scalars().all()]

    if domain == "restaurant":
        result = await db.execute(
            select(RestaurantRecommendation)
            .where(RestaurantRecommendation.user_id == user_id)
            .order_by(desc(RestaurantRecommendation.created_at))
            .limit(20)
        )
        dedup: dict[str, dict[str, Any]] = {}
        for recommendation in result.scalars().all():
            for restaurant in recommendation.restaurants or []:
                candidate = restaurant_candidate(recommendation.id, restaurant)
                dedup.setdefault(candidate["item_id"], candidate)
        return list(dedup.values())

    return []
