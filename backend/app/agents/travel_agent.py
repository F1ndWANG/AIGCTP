"""
Travel Agent — 旅行规划与调整

Orchestrates:
  1. Domain data fetching (POIs, weather, products)
  2. LLM itinerary generation via prompt_builder
  3. Post-processing (weather merge, theme sanitization, POI enforcement)
"""
import asyncio as _asyncio
import re

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.llm import llm_service
from app.services.progress import yield_progress
from app.agents.tools.poi_tools import search_scenic_spots, search_restaurants, search_hotels
from app.agents.tools.weather_tools import get_weather_forecast
from app.agents.domain_results import TravelAgentResult, TravelPlanArtifact
from app.agents.prompt_builder import (
    TRAVEL_SYSTEM_PROMPT,
    build_unified_itinerary_prompt,
    build_unified_adjustment_prompt,
)
from app.models.commerce import Product
from app.models.user import User
from app.core.logging import get_logger
from app.services.recommendation import recommendation_service
from app.services.recommendation.candidate import restaurant_candidate

logger = get_logger(__name__)

RELATED_POI_GROUPS = (
    ("天安门", "天安门广场", "天安门城楼", "天安门-城楼", "天安门广场-国旗"),
)


# ═══════════════════════════════════════════
# Data fetching
# ═══════════════════════════════════════════


async def _safe_fetch(coro, name: str, timeout: float = 15.0, default=None):
    """Execute a coroutine with timeout, returning default on failure."""
    try:
        return await _asyncio.wait_for(coro, timeout=timeout)
    except Exception as e:
        logger.warning("%s failed: %s", name, e)
        return default or []


def _travel_item_candidate(item: dict, *, destination: str, item_type: str, index: int) -> dict:
    name = item.get("name") or item.get("title") or item.get("poi") or f"{destination}推荐"
    rating = item.get("rating") or item.get("score") or 0
    return {
        "domain": "travel",
        "item_type": item_type,
        "item_id": str(item.get("id") or item.get("poi_id") or f"{item_type}:{index}:{name}"),
        "title": name,
        "subtitle": item.get("address") or destination,
        "description": item.get("description") or item.get("reason") or item.get("intro") or item.get("address"),
        "image_url": None,
        "url": None,
        "metadata": {
            "city": destination,
            "rating": float(rating or 0),
            "tags": item.get("tags") or item.get("type") or item.get("category"),
            "raw": item,
        },
    }


def _product_item_candidate(item: dict, *, index: int) -> dict:
    return {
        "domain": "commerce",
        "item_type": "product",
        "item_id": str(item.get("id") or f"product:{index}:{item.get('name', '')}"),
        "title": item.get("name") or "推荐好物",
        "subtitle": f"¥{float(item.get('price') or 0):.1f}",
        "description": item.get("description") or "适合本次行程的推荐好物",
        "image_url": None,
        "url": f"/products/{item.get('id')}" if item.get("id") else None,
        "metadata": {
            "price": item.get("price"),
            "rating": float(item.get("rating") or 0),
            "tags": item.get("tags") or [],
            "raw": item,
        },
    }


async def _rank_external_items(
    db: AsyncSession,
    *,
    user_id: int | None,
    destination: str,
    items: list[dict],
    domain: str,
    item_type: str,
    limit: int,
    context: dict,
) -> list[dict]:
    if not user_id or not items:
        return items[:limit]
    try:
        user = await db.get(User, user_id)
        if not user:
            return items[:limit]
        candidates = []
        for index, item in enumerate(items):
            if domain == "restaurant":
                candidates.append(restaurant_candidate(index, {**item, "city": item.get("city") or destination}))
            elif domain == "commerce":
                candidates.append(_product_item_candidate(item, index=index))
            else:
                candidates.append(_travel_item_candidate(item, destination=destination, item_type=item_type, index=index))
        ranked = await recommendation_service.rank_candidates(
            db,
            user=user,
            domain=domain,
            candidates=candidates,
            limit=limit,
            context=context,
            log=False,
        )
        raw_by_id = {candidate["item_id"]: candidate["metadata"]["raw"] for candidate in candidates}
        return [raw_by_id[item["item_id"]] for item in ranked if item["item_id"] in raw_by_id] or items[:limit]
    except Exception as e:
        logger.warning("Travel external recommendation ranking failed: %s", e)
        return items[:limit]


async def _fetch_domain_data(
    db: AsyncSession,
    destination: str,
    days: int,
    *,
    user_id: int | None = None,
    poi_limit: int = 12,
    restaurant_limit: int = 6,
    include_hotels: bool = True,
) -> tuple[list[dict], list[dict], list[dict], list[dict], list[dict]]:
    """Fetch POIs, restaurants, hotels, weather, and products in parallel."""
    from sqlalchemy import select

    async def _fetch_products():
        try:
            result = await db.execute(
                select(Product).where(Product.status == "active").order_by(Product.rating.desc()).limit(10)
            )
            return [
                {
                    "id": p.id,
                    "name": p.name,
                    "price": float(p.price),
                    "rating": float(p.rating or 0),
                    "description": p.description,
                    "tags": p.tags or [],
                }
                for p in result.scalars().all()
            ]
        except Exception as e:
            logger.warning("fetch_products failed: %s", e)
            return []

    hotels_coro = search_hotels(db, destination, limit=3) if include_hotels else None

    results = await _asyncio.gather(
        _safe_fetch(search_scenic_spots(db, destination, limit=poi_limit), "scenic_spots"),
        _safe_fetch(search_restaurants(db, destination, limit=restaurant_limit), "restaurants"),
        _safe_fetch(hotels_coro, "hotels") if hotels_coro is not None else _asyncio.sleep(0),
        _safe_fetch(get_weather_forecast(destination, days=days), "weather"),
        _safe_fetch(_fetch_products(), "products"),
    )
    pois, restaurants, hotels, weather, products = (
        results[0],
        results[1],
        results[2] if include_hotels else [],
        results[3],
        results[4],
    )
    context = {"destination": destination, "days": days}
    pois, restaurants, hotels, products = await _asyncio.gather(
        _rank_external_items(db, user_id=user_id, destination=destination, items=pois, domain="travel", item_type="poi", limit=poi_limit, context=context),
        _rank_external_items(db, user_id=user_id, destination=destination, items=restaurants, domain="restaurant", item_type="restaurant", limit=restaurant_limit, context=context),
        _rank_external_items(db, user_id=user_id, destination=destination, items=hotels, domain="travel", item_type="hotel", limit=3, context=context),
        _rank_external_items(db, user_id=user_id, destination=destination, items=products, domain="commerce", item_type="product", limit=10, context=context),
    )
    return pois, restaurants, hotels, weather, products


# ═══════════════════════════════════════════
# Post-processing helpers
# ═══════════════════════════════════════════


def _merge_weather_into_itinerary(itinerary: dict, weather: list[dict]) -> None:
    """Merge real weather data into itinerary — not reliant on LLM output."""
    if not itinerary or not weather:
        return
    day_by_day = itinerary.get("day_by_day")
    if not day_by_day:
        return
    for i, day in enumerate(day_by_day):
        w = weather[i] if i < len(weather) else weather[-1]
        if w:
            day.setdefault("weather", {})
            day["weather"]["condition"] = w.get("condition", day["weather"].get("condition", ""))
            day["weather"]["temp_min"] = w.get("temp_min", day["weather"].get("temp_min", ""))
            day["weather"]["temp_max"] = w.get("temp_max", day["weather"].get("temp_max", ""))


def _sanitize_theme(itinerary: dict, destination: str) -> None:
    """Ensure itinerary theme is meaningful, not a generic placeholder."""
    _remove_non_poi_activities(itinerary, destination)
    theme = (itinerary.get("theme") or "").strip()
    generic = {"", "行程", "调整后的行程", "修改后的行程", "调整", "修改",
               "新行程", "新调整", "调整后行程", "修改后行程",
               "围绕调整后的行程", "围绕修改后的行程", f"{destination}探索之旅",
               f"{destination}{itinerary.get('days', '')}日游", f"{destination}1日游"}
    if theme in generic or "规划" in theme:
        itinerary["theme"] = _theme_from_activities(itinerary, destination)

    for i, day in enumerate(itinerary.get("day_by_day", []) or []):
        dt = (day.get("theme") or "").strip()
        if not dt or dt in {"", "调整", "修改", "探索", "游玩", "调整后", "修改后"} or "规划" in dt:
            day_num = day.get("day", i + 1)
            acts = day.get("activities", []) or []
            if acts and acts[0].get("poi"):
                day["theme"] = f"{acts[0]['poi']}主题探索" if len(acts) == 1 else f"{acts[0]['poi']}到{acts[-1].get('poi', acts[0]['poi'])}"
            else:
                day["theme"] = f"第{day_num}天"


def _is_non_poi_activity_name(name: str, destination: str) -> bool:
    normalized = _normalize_poi_name(name)
    if not normalized:
        return True
    planning_prefixes = ("规划", "安排", "生成", "制定", "设计")
    if any(normalized.startswith(f"{prefix}{_normalize_poi_name(destination)}") for prefix in planning_prefixes):
        return True
    return normalized in {_normalize_poi_name(destination), f"{_normalize_poi_name(destination)}一日游"}


def _remove_non_poi_activities(itinerary: dict, destination: str) -> None:
    for day in itinerary.get("day_by_day", []) or []:
        activities = day.get("activities", []) or []
        day["activities"] = [
            act for act in activities
            if not _is_non_poi_activity_name(str(act.get("poi", "")), destination)
        ]


def _activity_names(itinerary: dict, *, limit: int = 3) -> list[str]:
    names: list[str] = []
    for day in itinerary.get("day_by_day", []) or []:
        for act in day.get("activities", []) or []:
            name = str(act.get("poi", "")).strip()
            if name and name not in names:
                names.append(name)
                if len(names) >= limit:
                    return names
    return names


def _theme_from_activities(itinerary: dict, destination: str) -> str:
    names = _activity_names(itinerary, limit=3)
    if len(names) >= 2:
        return f"{names[0]}、{names[1]}经典路线"
    if names:
        return f"{destination}{names[0]}深度探索"
    return f"{destination}经典一日游"


def _estimate_budget(days: int, restaurants: list[dict] | None = None, hotels: list[dict] | None = None) -> dict:
    food = 140 * max(days, 1)
    transport = 40 * max(days, 1)
    tickets = 120 * max(days, 1)
    hotel = 0 if days <= 1 else 520 * (days - 1)
    if hotels and days > 1:
        hotel = max(hotel, 500 * (days - 1))
    total = food + transport + tickets + hotel
    breakdown = {
        "餐饮": f"约 ¥{food}",
        "市内交通": f"约 ¥{transport}",
        "门票/预约": f"约 ¥{tickets}",
    }
    if hotel:
        breakdown["住宿"] = f"约 ¥{hotel}"
    return {"total": f"约 ¥{total}/人", "breakdown": breakdown}


# ═══════════════════════════════════════════
# POI name matching utilities
# ═══════════════════════════════════════════


def _normalize_poi_name(name: str) -> str:
    return re.sub(r"[\s\-·・—_()（）《》【】\[\]]+", "", name or "").lower()


def _poi_aliases(name: str) -> set[str]:
    normalized = _normalize_poi_name(name)
    aliases = {normalized}
    for suffix in ("博物院", "博物馆", "公园", "广场", "景区", "街区", "大街", "寺", "城楼"):
        if normalized.endswith(suffix):
            aliases.add(normalized[:-len(suffix)])
    for group in RELATED_POI_GROUPS:
        normalized_group = {_normalize_poi_name(item) for item in group}
        if normalized in normalized_group or any(alias in normalized_group for alias in aliases):
            aliases.update(normalized_group)
    return {a for a in aliases if a}


def _collect_activity_pois(itinerary: dict) -> list[str]:
    pois: list[str] = []
    for day in itinerary.get("day_by_day", []) or []:
        for act in day.get("activities", []) or []:
            poi = act.get("poi")
            if isinstance(poi, str) and poi:
                pois.append(poi)
    return pois


def _matches_excluded_poi(name: str, excluded_names: list[str]) -> bool:
    aliases = _poi_aliases(name)
    for excluded in excluded_names:
        if not aliases.isdisjoint(_poi_aliases(excluded)):
            return True
    return False


def _itinerary_contains_pois(itinerary: dict, excluded_names: list[str]) -> bool:
    return any(_matches_excluded_poi(p, excluded_names) for p in _collect_activity_pois(itinerary))


def _strip_excluded_activities(itinerary: dict, excluded_names: list[str]) -> None:
    for day in itinerary.get("day_by_day", []) or []:
        activities = day.get("activities", []) or []
        day["activities"] = [a for a in activities if not _matches_excluded_poi(str(a.get("poi", "")), excluded_names)]


def _dedupe_itinerary_activities(itinerary: dict) -> None:
    """Remove duplicate/near-duplicate activities across the whole itinerary."""
    seen_aliases: set[str] = set()
    for day in itinerary.get("day_by_day", []) or []:
        deduped = []
        for activity in day.get("activities", []) or []:
            poi = str(activity.get("poi", ""))
            aliases = _poi_aliases(poi)
            if aliases and aliases & seen_aliases:
                continue
            deduped.append(activity)
            seen_aliases.update(aliases)
        day["activities"] = deduped


def _dedupe_pois(pois: list[dict]) -> list[dict]:
    """Remove near-duplicate POIs such as 天安门 and 天安门广场."""
    deduped: list[dict] = []
    seen_aliases: set[str] = set()
    for poi in pois:
        name = str(poi.get("name", ""))
        aliases = _poi_aliases(name)
        if aliases & seen_aliases:
            continue
        deduped.append(poi)
        seen_aliases.update(aliases)
    return deduped


def _filter_excluded_pois(pois: list[dict], excluded_names: list[str]) -> list[dict]:
    if not excluded_names:
        return _dedupe_pois(pois)
    return _dedupe_pois([
        poi for poi in pois
        if not _matches_excluded_poi(str(poi.get("name", "")), excluded_names)
    ])


def _fill_itinerary_activities(
    itinerary: dict,
    candidate_pois: list[dict],
    excluded_names: list[str],
    *,
    min_activities_per_day: int = 3,
) -> None:
    """Fill removed activities with safe alternatives from candidate POIs."""
    candidates = _filter_excluded_pois(candidate_pois, excluded_names)
    used_aliases: set[str] = set()
    for poi in _collect_activity_pois(itinerary):
        used_aliases.update(_poi_aliases(poi))

    candidate_index = 0
    default_slots = ("上午", "下午", "晚上")
    for day in itinerary.get("day_by_day", []) or []:
        activities = day.setdefault("activities", [])
        while len(activities) < min_activities_per_day and candidate_index < len(candidates):
            candidate = candidates[candidate_index]
            candidate_index += 1
            name = str(candidate.get("name", ""))
            aliases = _poi_aliases(name)
            if not name or aliases & used_aliases:
                continue
            slot = default_slots[len(activities) % len(default_slots)]
            activities.append({
                "time": slot,
                "poi": name,
                "duration": "2小时",
                "description": f"参观{name}",
                "tips": "这是根据你的排除要求补充的替代景点。",
            })
            used_aliases.update(aliases)


# ═══════════════════════════════════════════
# User intent inference (POI requests/exclusions)
# ═══════════════════════════════════════════


def _infer_requested_pois(instruction: str) -> list[str]:
    patterns = [
        r"([一-鿿]{2,6}?)([一-鿿A-Za-z0-9·・]{2,20})(?:一日游|二日游|三日游|\d日游|游玩|旅行|旅游|攻略)",
        r"(?:我想去|想去|想加|加上|加入|加一个|补一个|安排|增加|顺路去|再去|还想去|一定要去|改去)\s*([一-鿿A-Za-z0-9·・、和与及\s]{2,40})",
        r"(?:把|将).{1,30}(?:换成|改成|替换成)\s*([一-鿿A-Za-z0-9·・、和与及\s]{2,40})",
        r"(?:上午|下午|晚上|中午|早上|第二天|第2天|第一天|第1天|第三天|第3天).{0,10}(?:去|安排|加上)\s*([一-鿿A-Za-z0-9·・、和与及\s]{2,40})",
    ]
    pois: list[str] = []
    stop_words = ("一下", "一些", "一点", "那里", "这里", "这个", "那个", "吧", "看看",
                  "逛逛", "玩玩", "游玩", "玩", "一趟", "附近", "周边", "可以吗", "行吗")
    for pattern in patterns:
        for match in re.finditer(pattern, instruction):
            raw = match.group(match.lastindex or 1)
            raw = re.split(r"[，。,.!！?？；;]|然后|再|顺便|但是|不过", raw)[0]
            for part in re.split(r"[、/]|和|与|及|\s+", raw):
                name = part.strip("，。,.!！?？ ")
                for prefix in ("帮我", "请", "规划", "安排", "制定", "生成", "设计"):
                    if name.startswith(prefix) and len(name) > len(prefix) + 1:
                        name = name[len(prefix):]
                for stop in stop_words:
                    if name.endswith(stop):
                        name = name[:-len(stop)]
                if name and len(name) >= 2 and name not in pois:
                    pois.append(name)
    return pois


def _infer_excluded_pois(instruction: str, current_itinerary: dict) -> list[str]:
    current_pois = _collect_activity_pois(current_itinerary)
    if not current_pois:
        return []
    replace_all = ("这几个", "这些", "全部", "全都", "都玩过", "都去过",
                   "都打卡", "经典景点")
    if any(m in instruction for m in replace_all):
        return current_pois
    normalized_instruction = _normalize_poi_name(instruction)
    return [p for p in current_pois if any(a and a in normalized_instruction for a in _poi_aliases(p))]


def infer_travel_constraints(instruction: str, current_itinerary: dict | None = None) -> dict[str, list[str]]:
    """Extract session-scoped travel constraints from a user instruction."""
    current_itinerary = current_itinerary or {}
    avoid_pois = _infer_excluded_pois(instruction, current_itinerary)
    requested_pois = [
        poi for poi in _infer_requested_pois(instruction)
        if not _matches_excluded_poi(poi, avoid_pois)
    ]
    return {
        "avoid_pois": avoid_pois,
        "requested_pois": requested_pois,
    }


def merge_travel_memory(
    current: dict | None,
    *,
    avoid_pois: list[str] | None = None,
    requested_pois: list[str] | None = None,
    last_adjustment: str | None = None,
) -> dict:
    """Merge travel constraints into conversation-scoped memory only."""
    memory = dict(current or {})

    def merge_names(key: str, names: list[str] | None) -> None:
        if not names:
            return
        existing = list(memory.get(key, []))
        existing_aliases: set[str] = set()
        for name in existing:
            existing_aliases.update(_poi_aliases(str(name)))
        for name in names:
            aliases = _poi_aliases(str(name))
            if aliases and aliases & existing_aliases:
                continue
            existing.append(name)
            existing_aliases.update(aliases)
        memory[key] = existing

    merge_names("avoid_pois", avoid_pois)
    merge_names("requested_pois", requested_pois)
    if last_adjustment:
        history = list(memory.get("adjustments", []))
        history.append(last_adjustment)
        memory["adjustments"] = history[-8:]
    return memory


def _ensure_requested_pois(itinerary: dict, requested_pois: list[str], instruction: str) -> None:
    """Ensure explicitly requested POIs appear in the itinerary."""
    day_by_day = itinerary.setdefault("day_by_day", [])
    if not day_by_day:
        day_by_day.append({"day": 1, "theme": "按需调整", "activities": []})

    existing = {_normalize_poi_name(p) for p in _collect_activity_pois(itinerary)}

    day_map = {"一": 0, "二": 1, "三": 2, "四": 3, "五": 4, "1": 0, "2": 1, "3": 2, "4": 3, "5": 4}
    target_idx = 0
    for key, idx in day_map.items():
        if f"第{key}天" in instruction and idx < len(day_by_day):
            target_idx = idx
            break

    target_day = day_by_day[target_idx]
    activities = target_day.setdefault("activities", [])

    # Infer time slots from instruction
    slots = [m for m in ("上午", "中午", "下午", "晚上") if m in instruction]
    default_slots = ["上午", "下午", "晚上"]
    while len(slots) < len(requested_pois):
        slots.append(default_slots[len(slots) % len(default_slots)])

    insert_at = 0
    for idx, poi in enumerate(requested_pois):
        normalized = _normalize_poi_name(poi)
        if not normalized or normalized in existing:
            continue
        new_activity = {
            "time": slots[idx],
            "poi": poi,
            "duration": "2小时",
            "description": f"根据你的要求安排{poi}",
            "tips": "已在对话中确认，同步到行程卡。",
        }
        if insert_at < len(activities):
            activities[insert_at] = new_activity
        else:
            activities.append(new_activity)
        insert_at += 1
        existing.add(normalized)

    if requested_pois:
        target_day["theme"] = f"{requested_pois[0]}主题探索"
        current_theme = (itinerary.get("theme") or "").strip()
        if not current_theme or current_theme in {"", "行程", "调整后的行程", "修改后的行程"}:
            itinerary["theme"] = f"围绕{requested_pois[0]}调整后的行程"


# ═══════════════════════════════════════════
# Fallback generation (LLM unavailable)
# ═══════════════════════════════════════════


def _should_use_fast_itinerary(days: int, original_message: str) -> bool:
    if days <= 1:
        return True
    return any(m in original_message for m in ("半日游", "一日游", "1日游", "一天", "当天往返"))


def _fallback_itinerary(
    destination: str,
    days: int,
    pois: list[dict],
    restaurants: list[dict] | None = None,
    hotels: list[dict] | None = None,
) -> dict:
    day_by_day = []
    safe_pois = _dedupe_pois(pois)
    restaurants = restaurants or []
    hotels = hotels or []
    for d in range(1, days + 1):
        day_pois = safe_pois[(d - 1) * 3:d * 3] if safe_pois else []
        lunch = restaurants[(d - 1) % len(restaurants)] if restaurants else {}
        dinner = restaurants[d % len(restaurants)] if restaurants else {}
        hotel = hotels[(d - 1) % len(hotels)] if hotels else {}
        first = day_pois[0].get("name") if day_pois else ""
        last = day_pois[-1].get("name") if len(day_pois) > 1 else first
        day_by_day.append({
            "day": d,
            "theme": f"{first}到{last}" if first and last and first != last else (f"{destination}{first}探索" if first else f"第{d}天探索"),
            "weather": {"condition": "适中"},
            "meals": [
                {
                    "type": "午餐",
                    "recommendation": lunch.get("reason") or "品尝当地特色美食",
                    "restaurant": lunch.get("name") or "附近特色餐厅",
                },
                {
                    "type": "晚餐",
                    "recommendation": dinner.get("reason") or "体验当地美食",
                    "restaurant": dinner.get("name") or "当地特色餐厅",
                },
            ],
            "activities": [
                {"time": ["上午", "下午", "晚上"][i] if i < 3 else "其他",
                 "poi": p.get("name", f"景点{i+1}"), "duration": "2小时",
                 "description": f"参观{p.get('name', '景点')}"}
                for i, p in enumerate(day_pois)
            ],
            "shopping": [],
            "hotel": {
                "name": hotel.get("name") or f"{destination}核心商圈舒适型酒店",
                "price_level": hotel.get("price_level") or "约 ¥350-700/晚",
                "reason": hotel.get("reason") or "建议住在核心商圈或地铁换乘站附近，减少短途行程通勤时间。",
                "tips": hotel.get("tips") or "优先选择近地铁、可寄存行李、可免费取消、评分 4.5+ 的房型。",
            },
            "transport_tips": "建议乘坐公共交通",
        })
    itinerary = {
        "destination": destination, "days": days, "theme": f"{destination}经典一日游",
        "day_by_day": day_by_day, "budget_estimate": _estimate_budget(days, restaurants, hotels),
        "tips": [f"建议提前查看{destination}天气预报", "热门景区请提前确认开放时间和预约要求"],
    }
    itinerary["theme"] = _theme_from_activities(itinerary, destination)
    return itinerary


def _fallback_summary(destination: str, days: int, itinerary: dict, weather: list[dict]) -> str:
    day_by_day = itinerary.get("day_by_day", []) or []
    highlights: list[str] = []
    for day in day_by_day[:days]:
        for act in day.get("activities", []) or []:
            poi = act.get("poi")
            if poi and poi not in highlights:
                highlights.append(str(poi))
            if len(highlights) >= 4:
                break
        if len(highlights) >= 4:
            break
    weather_note = ""
    if weather:
        w = weather[0]
        weather_note = f"预计天气{w.get('condition','')}，气温约{w.get('temp_min','')}~{w.get('temp_max','')}℃，"
    hl = "、".join(highlights) if highlights else f"{destination}核心景点"
    return (f"已为你生成{destination}{days}日游方案。{weather_note}"
            f"整体行程围绕{hl}展开，兼顾经典景点、餐饮体验和交通便利性。"
            "建议提前确认景区开放时间和预约要求，出行当天优先使用公共交通。")


# ═══════════════════════════════════════════
# Main entry points
# ═══════════════════════════════════════════


async def plan_trip(
    destination: str,
    days: int,
    user_id: int,
    db: AsyncSession,
    user_preferences: dict | None = None,
    original_message: str = "",
    reporter=None,
    conversation_messages: list[dict] | None = None,
    avoid_pois: list[str] | None = None,
) -> TravelAgentResult:
    """Generate a new travel plan."""
    if user_preferences is None:
        user_preferences = {}

    await yield_progress(reporter, f"正在搜索{destination}的景点和美食...")
    pois, restaurants, hotels, weather, products = await _fetch_domain_data(
        db,
        destination,
        days,
        user_id=user_id,
        poi_limit=12,
        restaurant_limit=6,
        include_hotels=True,
    )
    pois = _filter_excluded_pois(pois, avoid_pois or [])

    # Fast path: small trips use deterministic planning
    if _should_use_fast_itinerary(days, original_message):
        itinerary = _fallback_itinerary(destination, days, pois, restaurants, hotels)
        requested_pois = [p for p in _infer_requested_pois(original_message)
                          if _normalize_poi_name(p) != _normalize_poi_name(destination)]
        if requested_pois:
            _ensure_requested_pois(itinerary, requested_pois, original_message)
        _dedupe_itinerary_activities(itinerary)
        _merge_weather_into_itinerary(itinerary, weather)
        _sanitize_theme(itinerary, destination)
        summary = _fallback_summary(destination, days, itinerary, weather)
        if requested_pois:
            summary = f"已将 {', '.join(requested_pois)} 同步到行程卡。\n\n{summary}"
        return TravelAgentResult(response=summary, travel_plan=TravelPlanArtifact(
            destination=destination, days=days, itinerary=itinerary, preferences=user_preferences,
        ))

    await yield_progress(reporter, "正在生成行程方案...")
    requested_pois = [p for p in _infer_requested_pois(original_message)
                      if _normalize_poi_name(p) != _normalize_poi_name(destination)]
    conv_history = _format_conversation_history(conversation_messages) if conversation_messages else ""
    prompt = build_unified_itinerary_prompt(
        destination, days, user_preferences, pois, restaurants, hotels, weather, products,
        original_message, conversation_history=conv_history,
        requested_poi_names=requested_pois or None,
        excluded_poi_names=avoid_pois or None,
    )

    try:
        result = await _asyncio.wait_for(
            llm_service.chat_with_artifact(
                system_prompt=TRAVEL_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2800,
                temperature=0.7,
            ),
            timeout=45,
        )
        summary = result["text"]
        itinerary = result["artifact"]
    except Exception as e:
        logger.warning("LLM unified generation failed: %s", e)
        summary = ""
        itinerary = None

    if not isinstance(itinerary, dict) or not itinerary.get("day_by_day"):
        itinerary = _fallback_itinerary(destination, days, pois, restaurants, hotels)
        if not summary:
            summary = _fallback_summary(destination, days, itinerary, weather)

    await yield_progress(reporter, "正在优化行程细节...")
    if requested_pois:
        _ensure_requested_pois(itinerary, requested_pois, original_message)
    _dedupe_itinerary_activities(itinerary)
    _merge_weather_into_itinerary(itinerary, weather)
    if avoid_pois and _itinerary_contains_pois(itinerary, avoid_pois):
        _strip_excluded_activities(itinerary, avoid_pois)
        _fill_itinerary_activities(itinerary, pois, avoid_pois)
    _sanitize_theme(itinerary, destination)

    return TravelAgentResult(response=summary, travel_plan=TravelPlanArtifact(
        destination=destination, days=days, itinerary=itinerary, preferences=user_preferences,
    ))


async def adjust_plan(
    plan_id: int,
    instruction: str,
    current_itinerary: dict,
    destination: str,
    days: int,
    db: AsyncSession,
    user_id: int | None = None,
    reporter=None,
    conversation_messages: list[dict] | None = None,
    avoid_pois: list[str] | None = None,
) -> TravelAgentResult:
    """Adjust an existing travel plan — unified LLM call for response + itinerary."""
    if user_id is not None:
        from sqlalchemy import select
        from app.models.travel import TravelPlan
        result = await db.execute(
            select(TravelPlan).where(TravelPlan.id == plan_id, TravelPlan.user_id == user_id))
        if not result.scalar_one_or_none():
            return TravelAgentResult(response="抱歉，未找到该行程或无权限修改。", travel_plan=None)

    await yield_progress(reporter, "正在分析你的调整需求...")
    await yield_progress(reporter, f"正在搜索{destination}的景点、餐厅和天气...")

    pois, restaurants, _, weather, products = await _fetch_domain_data(
        db,
        destination,
        days,
        user_id=user_id,
        poi_limit=20,
        restaurant_limit=10,
        include_hotels=False,
    )

    excluded_pois = merge_travel_memory(
        {},
        avoid_pois=avoid_pois or [],
    ).get("avoid_pois", [])
    inferred_excluded = _infer_excluded_pois(instruction, current_itinerary)
    excluded_pois = merge_travel_memory(
        {"avoid_pois": excluded_pois},
        avoid_pois=inferred_excluded,
    ).get("avoid_pois", [])
    requested_pois = [
        poi for poi in _infer_requested_pois(instruction)
        if not _matches_excluded_poi(poi, excluded_pois)
    ]
    safe_pois = _filter_excluded_pois(pois, excluded_pois)

    await yield_progress(reporter, "正在通过AI重新规划行程...")
    conv_history = _format_conversation_history(conversation_messages) if conversation_messages else ""
    prompt = build_unified_adjustment_prompt(
        instruction, current_itinerary, safe_pois, restaurants, weather, products,
        excluded_poi_names=excluded_pois, requested_poi_names=requested_pois,
        conversation_history=conv_history,
    )

    itinerary = None
    summary = ""
    for attempt in range(2):
        try:
            result = await _asyncio.wait_for(
                llm_service.chat_with_artifact(
                    system_prompt=TRAVEL_SYSTEM_PROMPT,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=2800,
                    temperature=0.7,
                ),
                timeout=45,
            )
            summary = result["text"]
            itinerary = result["artifact"]
        except Exception as e:
            logger.warning("adjust_plan unified attempt %d failed: %s", attempt + 1, e)

        if isinstance(itinerary, dict) and itinerary.get("day_by_day"):
            if excluded_pois and _itinerary_contains_pois(itinerary, excluded_pois):
                if attempt == 0:
                    prompt += ("\n\n!! 严重警告 !! 你上一次的输出仍然包含了用户明确要求排除的景点。"
                               "请重新生成，绝对不要包含被排除的景点。\n"
                               f"被排除的景点: {', '.join(excluded_pois)}")
                    itinerary = None
                    continue
            break
        if attempt == 0:
            prompt += "\n\n请确保输出完整的 JSON 代码块。"

    if not isinstance(itinerary, dict) or not itinerary.get("day_by_day"):
        itinerary = _fallback_itinerary(destination, days, safe_pois, restaurants, [])
        itinerary["theme"] = f"{destination}调整后行程"
        if not summary:
            summary = _fallback_summary(destination, days, itinerary, weather)

    if excluded_pois and _itinerary_contains_pois(itinerary, excluded_pois):
        _strip_excluded_activities(itinerary, excluded_pois)
    if requested_pois:
        _ensure_requested_pois(itinerary, requested_pois, instruction)
    _dedupe_itinerary_activities(itinerary)
    if excluded_pois:
        _fill_itinerary_activities(itinerary, safe_pois, excluded_pois)

    _merge_weather_into_itinerary(itinerary, weather)
    _sanitize_theme(itinerary, destination)

    if excluded_pois:
        excluded_text = "、".join(excluded_pois)
        summary = f"已根据你的要求避开 {excluded_text} 及相关景点，并为你补充了替代安排。\n\n{summary}"
    if requested_pois:
        summary = f"已将 {', '.join(requested_pois)} 同步到行程卡。\n\n{summary}"

    return TravelAgentResult(response=summary, travel_plan=TravelPlanArtifact(
        destination=destination, days=days, itinerary=itinerary, preferences={},
    ))


# ═══════════════════════════════════════════
# Conversation history formatting
# ═══════════════════════════════════════════


def _format_conversation_history(messages: list[dict], limit: int = 6) -> str:
    """Format recent conversation messages as context for the LLM prompt."""
    recent = messages[-limit:] if len(messages) > limit else messages
    lines = []
    for m in recent:
        role = "用户" if m.get("role") == "user" else "AI"
        content = (m.get("content") or "")[:200]
        lines.append(f"{role}: {content}")
    return "\n".join(lines)
