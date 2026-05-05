"""POI search tools for Travel Agent"""
import json
from typing import Optional

from app.services.amap import amap_service
from app.models.cache import CachedPOI
from app.core.cache import get_list, set_list
from app.core.config import settings
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select


def _to_str(val, default=""):
    if val is None:
        return default
    if isinstance(val, (list, dict)):
        return default
    return str(val)


def _to_float(val):
    if val is None:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def _to_list(val):
    if isinstance(val, list):
        return val
    if isinstance(val, str):
        try:
            parsed = json.loads(val)
            return parsed if isinstance(parsed, list) else []
        except (json.JSONDecodeError, TypeError):
            return []
    return []


async def search_pois(
    db: AsyncSession,
    keywords: str,
    city: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 20,
) -> list[dict]:
    """搜索景点/POI，优先查缓存"""
    # Try Redis cache first
    cache_key = f"poi:search:{city or ''}:{keywords}:{category or ''}:{limit}"
    cached = await get_list(cache_key)
    if cached:
        return cached[:limit]

    # Try DB cache next
    stmt = select(CachedPOI)
    if city:
        stmt = stmt.where(CachedPOI.name.ilike(f"%{keywords}%") | CachedPOI.tags.contains([keywords]))
    stmt = stmt.limit(limit)
    result = await db.execute(stmt)
    cached = result.scalars().all()

    if len(cached) >= limit * 0.8:
        return [
            {
                "poi_id": p.poi_id,
                "name": p.name,
                "latitude": p.latitude,
                "longitude": p.longitude,
                "category": p.category,
                "address": p.address,
                "rating": p.rating,
                "tags": p.tags,
                "image_urls": p.image_urls,
            }
            for p in cached
        ]

    # Fall back to API
    api_types = category or None
    pois = await amap_service.search_poi(keywords, city=city, types=api_types, page_size=limit)

    # Cache results — safe type conversions for SQLite compatibility
    for poi in pois[:limit]:
        existing = await db.execute(
            select(CachedPOI).where(CachedPOI.name == poi["name"], CachedPOI.source == "amap")
        )
        if not existing.scalar_one_or_none():
            # Write to Redis cache
            await set_list(cache_key, pois[:limit], ttl=settings.REDIS_TTL_POI)

            db.add(CachedPOI(
                source="amap",
                poi_id=_to_str(poi.get("poi_id"), None),
                name=poi["name"],
                latitude=_to_float(poi.get("latitude")),
                longitude=_to_float(poi.get("longitude")),
                category=_to_str(poi.get("category")),
                tags=_to_list(poi.get("tags")),
                rating=_to_float(poi.get("rating")),
                address=_to_str(poi.get("address")),
                phone=_to_str(poi.get("phone")),
                opening_hours=_to_str(poi.get("opening_hours")),
                image_urls=_to_list(poi.get("image_urls")),
                raw_data=poi,
            ))

    return pois[:limit]


async def search_scenic_spots(db: AsyncSession, city: str, limit: int = 20) -> list[dict]:
    """搜索景点"""
    return await search_pois(db, "景点", city=city, category="风景名胜", limit=limit)


async def search_restaurants(
    db: AsyncSession,
    city: str,
    cuisine: Optional[str] = None,
    limit: int = 10,
) -> list[dict]:
    """搜索餐厅"""
    keywords = cuisine if cuisine else "美食"
    pois = await amap_service.search_restaurants(city, keywords=keywords, page_size=limit)
    return [
        {
            "name": p["name"],
            "address": p.get("address", ""),
            "rating": p.get("rating"),
            "category": p.get("category", ""),
            "tags": p.get("tags", []),
            "longitude": p.get("longitude"),
            "latitude": p.get("latitude"),
            "phone": p.get("phone", ""),
        }
        for p in pois
    ]


async def search_hotels(db: AsyncSession, city: str, limit: int = 10) -> list[dict]:
    """搜索酒店"""
    pois = await amap_service.search_hotels(city, page_size=limit)
    return [
        {
            "name": p["name"],
            "address": p.get("address", ""),
            "rating": p.get("rating"),
            "tags": p.get("tags", []),
            "longitude": p.get("longitude"),
            "latitude": p.get("latitude"),
        }
        for p in pois
    ]


async def get_route(
    origin: tuple[float, float],
    destination: tuple[float, float],
    mode: str = "transit",
) -> dict:
    """获取路线信息"""
    return await amap_service.get_direction(origin, destination, mode=mode)


async def geocode_address(address: str, city: Optional[str] = None) -> Optional[dict]:
    """地址转坐标"""
    return await amap_service.geocode(address, city=city)
