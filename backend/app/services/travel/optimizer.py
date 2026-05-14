from __future__ import annotations

from typing import Any

from app.services.travel.constraints import normalize_name, parse_constraints
from app.services.travel.scoring import score_hotel, score_poi, score_product, score_restaurant


TIME_SLOTS = {
    "relaxed": ["上午", "下午"],
    "balanced": ["上午", "下午", "晚上"],
    "compact": ["上午", "中午", "下午", "晚上"],
}


def _dedupe_named(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    output: list[dict[str, Any]] = []
    for item in items:
        name = normalize_name(str(item.get("name") or item.get("title") or ""))
        if not name or name in seen:
            continue
        seen.add(name)
        output.append(item)
    return output


def _ordered_pois(destination: str, pois: list[dict[str, Any]], constraints: dict[str, Any]) -> list[dict[str, Any]]:
    scored = []
    for poi in _dedupe_named(pois):
        score = score_poi(poi, constraints, destination)
        if score >= 0:
            scored.append((score, poi))
    scored.sort(key=lambda item: item[0], reverse=True)

    must_names = [normalize_name(item) for item in constraints.get("must_visit") or []]
    required = []
    remaining = []
    for score, poi in scored:
        name = normalize_name(str(poi.get("name") or ""))
        if any(req and (req in name or name in req) for req in must_names):
            required.append((score, poi))
        else:
            remaining.append((score, poi))
    return [poi for _, poi in [*required, *remaining]]


def _duration(slot: str) -> str:
    return "1.5小时" if slot == "中午" else "2小时"


def _budget(days: int, restaurants: list[dict[str, Any]], hotels: list[dict[str, Any]], constraints: dict[str, Any]) -> dict[str, Any]:
    food = 90 * days
    traffic = 35 * days
    ticket = 80 * days
    hotel = 0
    if days > 1:
        hotel = 450 * max(days - 1, 1)
    estimate = food + traffic + ticket + hotel
    if constraints.get("budget"):
        estimate = min(estimate, float(constraints["budget"]))
    return {
        "total": f"约 ¥{int(estimate)}/人",
        "breakdown": {
            "餐饮": f"约 ¥{food}",
            "交通": f"约 ¥{traffic}",
            "门票": f"约 ¥{ticket}",
            "住宿": f"约 ¥{hotel}" if hotel else "当日往返可不计住宿",
        },
    }


def optimize_itinerary(
    *,
    destination: str,
    days: int,
    pois: list[dict[str, Any]],
    restaurants: list[dict[str, Any]] | None = None,
    hotels: list[dict[str, Any]] | None = None,
    products: list[dict[str, Any]] | None = None,
    weather: list[dict[str, Any]] | None = None,
    user_preferences: dict[str, Any] | None = None,
    original_message: str = "",
    requested_pois: list[str] | None = None,
    avoid_pois: list[str] | None = None,
) -> dict[str, Any]:
    constraints = parse_constraints(
        original_message,
        user_preferences,
        requested_pois=requested_pois,
        avoid_pois=avoid_pois,
    )
    restaurants = sorted(restaurants or [], key=lambda item: score_restaurant(item, constraints), reverse=True)
    hotels = sorted(hotels or [], key=lambda item: score_hotel(item, constraints, destination), reverse=True)
    products = sorted(products or [], key=lambda item: score_product(item, constraints, destination), reverse=True)
    ordered_pois = _ordered_pois(destination, pois, constraints)

    slots = TIME_SLOTS.get(constraints["pace"], TIME_SLOTS["balanced"])
    day_by_day = []
    poi_index = 0
    for day in range(1, days + 1):
        day_slots = slots[:]
        activities = []
        for slot in day_slots:
            if poi_index >= len(ordered_pois):
                break
            poi = ordered_pois[poi_index]
            poi_index += 1
            name = poi.get("name") or poi.get("title") or f"{destination}景点"
            activities.append(
                {
                    "time": slot,
                    "poi": name,
                    "duration": _duration(slot),
                    "description": poi.get("reason") or poi.get("description") or f"参观{name}，兼顾兴趣匹配和路线顺畅度。",
                    "tips": "由约束优化排序，已避开不感兴趣地点。",
                }
            )

        lunch = restaurants[(day - 1) % len(restaurants)] if restaurants else {}
        dinner = restaurants[day % len(restaurants)] if restaurants else {}
        hotel = hotels[(day - 1) % len(hotels)] if hotels else {}
        first = activities[0]["poi"] if activities else destination
        last = activities[-1]["poi"] if activities else destination
        day_by_day.append(
            {
                "day": day,
                "theme": f"{first}到{last}" if first != last else f"{first}主题探索",
                "weather": _weather_for_day(weather, day),
                "meals": [
                    {
                        "type": "午餐",
                        "restaurant": lunch.get("name") or "附近特色餐厅",
                        "recommendation": lunch.get("reason") or f"优先选择{constraints.get('cuisine') or '本地特色'}和动线附近餐厅",
                        "description": lunch.get("address") or lunch.get("description") or "",
                    },
                    {
                        "type": "晚餐",
                        "restaurant": dinner.get("name") or "当地特色餐厅",
                        "recommendation": dinner.get("reason") or "晚餐安排在最后一个景点附近，减少返程绕路",
                        "description": dinner.get("address") or dinner.get("description") or "",
                    },
                ],
                "activities": activities,
                "shopping": [
                    {
                        "product_id": product.get("id"),
                        "product_name": product.get("name") or product.get("title") or "旅行好物",
                        "price": float(product.get("price") or 0),
                        "reason": product.get("reason") or "根据行程场景推荐，适合出行携带。",
                    }
                    for product in products[:1]
                ],
                "hotel": {
                    "name": hotel.get("name") or f"{destination}地铁沿线舒适型酒店",
                    "price_level": hotel.get("price_level") or "约 ¥400-700/晚",
                    "reason": hotel.get("reason") or "优先选择靠近主要景点或地铁换乘站的位置，减少跨城通勤。",
                    "tips": hotel.get("tips") or "建议选择可免费取消、评分较高、可寄存行李的房型。",
                },
                "transport_tips": f"默认使用{constraints['transport']}，相邻景点按兴趣和动线启发式排序。",
            }
        )

    theme_pois = [activity["poi"] for day in day_by_day for activity in day.get("activities", [])][:3]
    theme = f"{destination}{'、'.join(theme_pois)}之旅" if theme_pois else f"{destination}约束优化行程"
    return {
        "destination": destination,
        "days": days,
        "theme": theme,
        "day_by_day": day_by_day,
        "budget_estimate": _budget(days, restaurants, hotels, constraints),
        "tips": [
            "行程顺序由约束优化生成，兼顾兴趣、预算、餐饮和交通顺畅度。",
            "热门景区请提前确认开放时间和预约要求。",
            f"当前节奏：{constraints['pace']}；交通偏好：{constraints['transport']}。",
        ],
        "optimization": {
            "algorithm": "constraint_heuristic_v1",
            "constraints": constraints,
            "objectives": ["preference_match", "route_smoothness", "budget_fit", "diversity"],
        },
    }


def _weather_for_day(weather: list[dict[str, Any]] | None, day: int) -> dict[str, Any]:
    if not weather:
        return {"condition": "适中"}
    item = weather[min(day - 1, len(weather) - 1)] or {}
    return {
        "condition": item.get("condition", "适中"),
        "temp_min": item.get("temp_min", ""),
        "temp_max": item.get("temp_max", ""),
    }
