"""
Travel Agent - 旅行规划助手

Uses LangGraph to orchestrate travel planning:
  1. Intent parsing (destination, days, preferences)
  2. Parallel tool calls (POI + weather + user preferences)
  3. LLM itinerary generation
  4. Structured output
"""
import json
import re
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.llm import llm_service
from app.agents.tools.poi_tools import search_scenic_spots, search_restaurants, search_hotels, get_route
from app.agents.tools.weather_tools import get_weather_forecast
from app.agents.domain_results import TravelAgentResult, TravelPlanArtifact
from app.models.commerce import Product
from app.core.logging import get_logger

logger = get_logger(__name__)

# ──────────────────────────────────────────────
# System prompt for the Travel Agent
# ──────────────────────────────────────────────

TRAVEL_SYSTEM_PROMPT = """你是 AI 生活推荐系统的旅行规划专家。你擅长根据用户的需求规划详细的旅行行程，并自然地融入美食推荐和购物建议。

## 你的角色
- 你是一个热情、专业的旅行规划师
- 你会考虑用户的偏好、预算、时间和天气等因素
- 你会推荐合理的景点顺序，考虑地理位置相邻性和交通便利性
- 你会在行程中自然地融入当地美食推荐
- 你会在每天的行程中推荐相关的商品（旅行装备、当地特产、实用好物）

## 行程规划原则
1. **节奏合理**: 每天安排 3-4 个活动，避免太赶
2. **地理位置优化**: 同区域的景点安排在相邻时段
3. **天气适应**: 雨天安排室内活动，晴天安排户外
4. **餐饮融入**: 每餐推荐当地特色餐厅或美食
5. **预算透明**: 给出大致预算估算
6. **购物推荐**: 每天推荐 1-2 件实用商品（旅行装备、当地特产、文创纪念品）

## 输出格式
你必须严格按照 JSON 格式输出行程规划，包含完整的 day_by_day 结构。
"""


def _build_itinerary_prompt(
    destination: str,
    days: int,
    user_preferences: dict,
    pois: list[dict],
    restaurants: list[dict],
    hotels: list[dict],
    weather: list[dict],
    products: list[dict] | None = None,
    original_message: str = "",
) -> str:
    """Build the prompt for itinerary generation (compact format)."""
    poi_lines = []
    for p in pois:
        poi_lines.append(f"  - {p.get('name', '?')} ({p.get('category', '')}) rating:{p.get('rating','')} {p.get('address','')[:30]}")
    poi_str = "\n".join(poi_lines[:15])

    rest_lines = []
    for r in restaurants:
        rest_lines.append(f"  - {r.get('name', '?')} ({r.get('category', '')}) rating:{r.get('rating','')}")
    rest_str = "\n".join(rest_lines[:8])

    weather_lines = [f"  - {w.get('date','')}: {w.get('condition','')} {w.get('temp_min','')}~{w.get('temp_max','')}C" for w in weather]
    weather_str = "\n".join(weather_lines) or "  (暂无天气数据)"

    prod_lines = []
    if products:
        for p in products:
            prod_lines.append(f"  - {p.get('name', '?')} ¥{p.get('price',0)} tags:{','.join(p.get('tags', []) or [])[:40]}")
    prod_str = "\n".join(prod_lines[:10]) if prod_lines else "  (暂无商品数据)"

    pref_str = json.dumps(user_preferences, ensure_ascii=False)

    return f"""请为以下旅行需求生成详细的行程规划：

## 目的地: {destination}
## 天数: {days}天


## 用户原始需求
{original_message or "未提供"}


## 用户偏好
{pref_str}

## 可用景点/POI
{poi_str}

## 可用餐厅
{rest_str}

## 可用商品（旅行装备/特产/实用好物）
{prod_str}

## 天气预报
{weather_str}

## 要求
请生成一个完整的 Day-by-Day 行程规划，JSON 格式如下：
{{
  "destination": "{destination}",
  "days": {days},
  "theme": "行程主题概括",
  "day_by_day": [
    {{
      "day": 1,
      "theme": "当日主题",
      "weather": {{"condition": "天气状况", "temp_min": "最低温", "temp_max": "最高温"}},
      "meals": [
        {{"type": "早餐", "recommendation": "推荐内容", "restaurant": "餐厅名", "description": "推荐理由"}},
        {{"type": "午餐", "recommendation": "推荐内容", "restaurant": "餐厅名", "description": "推荐理由"}},
        {{"type": "晚餐", "recommendation": "推荐内容", "restaurant": "餐厅名", "description": "推荐理由"}}
      ],
      "activities": [
        {{"time": "上午/下午/晚上", "poi": "景点名称", "duration": "建议时长", "description": "活动描述", "tips": "小贴士"}}
      ],
      "shopping": [
        {{"product_id": 商品ID, "product_name": "商品名称", "price": 价格, "reason": "推荐理由（为什么适合这个行程）"}}
      ],
      "hotel": {{"name": "酒店名称", "price_level": "经济/舒适/豪华", "reason": "推荐理由", "tips": "入住提示"}},
      "transport_tips": "交通建议"
    }}
  ],
  "budget_estimate": {{
    "total": "总预算范围",
    "breakdown": {{"住宿": "xxx", "餐饮": "xxx", "门票": "xxx", "交通": "xxx", "购物": "xxx"}}
  }},
  "tips": ["tip1", "tip2", "tip3"]
}}

请确保：
1. 景点顺序合理，同区域景点安排在一起
2. 每天节奏均衡，不要太赶
3. 融入当地特色美食推荐
4. 根据天气调整活动安排，务必在每天的 weather 字段中包含 condition、temp_min、temp_max
5. 每天推荐 1-2 件商品（从可用商品列表中选取），给出具体的推荐理由
6. 推荐要具体、有实际价值


7. 如果用户原始需求中点名了具体景点、街区或地点，必须把这些地点写入对应 day_by_day.activities

"""


def _merge_weather_into_itinerary(itinerary: dict, weather: list[dict]) -> None:
    """Merge weather data into each day's itinerary after LLM generation.
    This ensures weather always displays regardless of LLM output.
    """
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


def _build_adjustment_prompt(
    instruction: str,
    current_itinerary: dict,
    pois: list[dict],
    restaurants: list[dict],
    weather: list[dict],
    products: list[dict] | None = None,
) -> str:
    """Build prompt for adjusting an existing itinerary."""
    itinerary_str = json.dumps(current_itinerary, ensure_ascii=False, indent=2)
    poi_str = json.dumps(pois[:20], ensure_ascii=False, indent=2)
    rest_str = json.dumps(restaurants[:10], ensure_ascii=False, indent=2)
    weather_str = json.dumps(weather, ensure_ascii=False, indent=2)

    prod_lines = []
    if products:
        for p in products:
            prod_lines.append(f"  - {p.get('name', '?')} ¥{p.get('price',0)} tags:{','.join(p.get('tags', []) or [])[:40]}")
    prod_str = "\n".join(prod_lines[:10]) if prod_lines else "  (暂无商品数据)"

    return f"""用户对现有行程不满意，请根据反馈调整行程：

## 用户反馈
{instruction}

## 当前行程
{itinerary_str}

## 可用景点/POI
{poi_str}

## 可用餐厅
{rest_str}

## 可用商品（旅行装备/特产/实用好物）
{prod_str}

## 天气预报
{weather_str}

请重新生成完整的 Day-by-Day 行程规划（JSON 格式），确保用户反馈的问题已解决。
每天的规划中请包含 shopping 数组字段，推荐 1-2 件适合该行程的商品。
"""


# ──────────────────────────────────────────────
# Travel Agent Main Logic
# ──────────────────────────────────────────────

async def plan_trip(
    destination: str,
    days: int,
    user_id: int,
    db: AsyncSession,
    user_preferences: dict | None = None,
    original_message: str = "",
    reporter=None,
) -> TravelAgentResult:
    """Main entry point for travel planning.

    Args:
        reporter: optional ProgressReporter for streaming step-by-step updates
    Returns:
        dict with keys: response (str), travel_plan (dict with destination, days, itinerary, preferences)
    """
    if user_preferences is None:
        user_preferences = {}

    import asyncio
    from sqlalchemy import select

    from app.services.progress import yield_progress
    try:
        await yield_progress(reporter, f"正在搜索{destination}的景点和美食...")
    except Exception:
        pass

    async def safe_call(coro, name: str, default=None):
        try:
            return await asyncio.wait_for(coro, timeout=15)
        except Exception as e:
            logger.warning("%s failed: %s", name, e)
            return default or []

    pois_task = safe_call(search_scenic_spots(db, destination, limit=12), "scenic_spots")
    restaurants_task = safe_call(search_restaurants(db, destination, limit=6), "restaurants")
    hotels_task = safe_call(search_hotels(db, destination, limit=3), "hotels")
    weather_task = safe_call(get_weather_forecast(destination, days=days), "weather")

    # Fetch travel-related products
    async def fetch_products():
        try:
            result = await db.execute(
                select(Product).where(Product.status == "active").order_by(Product.rating.desc()).limit(10)
            )
            return [{"id": p.id, "name": p.name, "price": p.price, "tags": p.tags or []} for p in result.scalars().all()]
        except Exception as e:
            logger.warning("fetch_products failed: %s", e)
            return []

    pois, restaurants, hotels, weather, products = await asyncio.gather(
        pois_task, restaurants_task, hotels_task, weather_task, fetch_products(),
    )

    try:
        await yield_progress(reporter, "正在生成行程方案...")
    except Exception:
        pass

    # Step 2: Generate itinerary via LLM (with retry)
    itinerary_prompt = _build_itinerary_prompt(
        destination, days, user_preferences, pois, restaurants, hotels, weather, products, original_message,
    )

    itinerary = None
    for attempt in range(2):
        try:
            itinerary = await asyncio.wait_for(
                llm_service.extract_json(
                    system_prompt=TRAVEL_SYSTEM_PROMPT,
                    messages=[{"role": "user", "content": itinerary_prompt}],
                ),
                timeout=60,
            )
            break
        except Exception as e:
            logger.warning("LLM extract_json attempt %d failed: %s", attempt + 1, e)
            if attempt == 0:
                itinerary_prompt += "\n\nNote: Please respond quickly and keep the JSON concise."
            else:
                itinerary = _fallback_itinerary(destination, days, pois)

    if itinerary is None:
        itinerary = _fallback_itinerary(destination, days, pois)



    if not isinstance(itinerary, dict) or not itinerary.get("day_by_day"):
        itinerary = _fallback_itinerary(destination, days, pois)

    try:
        await yield_progress(reporter, "正在优化行程细节...")
    except Exception:
        pass

    requested_pois = _infer_requested_pois(original_message)
    requested_pois = [poi for poi in requested_pois if _normalize_poi_name(poi) != _normalize_poi_name(destination)]
    if requested_pois:
        _ensure_requested_pois(itinerary, requested_pois, original_message)


    # Step 3: Merge real weather data into itinerary (not reliant on LLM output)
    _merge_weather_into_itinerary(itinerary, weather)

    # Step 4: Build natural language response summary
    try:
        await yield_progress(reporter, "正在生成推荐语...")
    except Exception:
        pass
    summary = await _generate_summary(destination, days, itinerary, weather, user_preferences)


    if requested_pois:
        summary = f"已将 {', '.join(requested_pois)} 同步到行程卡。\n\n{summary}"


    return TravelAgentResult(
        response=summary,
        travel_plan=TravelPlanArtifact(
            destination=destination,
            days=days,
            itinerary=itinerary,
            preferences=user_preferences,
        ),
    )


async def adjust_plan(
    plan_id: int,
    instruction: str,
    current_itinerary: dict,
    destination: str,
    days: int,
    db: AsyncSession,
    user_id: int | None = None,
) -> TravelAgentResult:
    """Adjust an existing travel plan based on user feedback."""
    if user_id is not None:
        from sqlalchemy import select
        from app.models.travel import TravelPlan
        result = await db.execute(
            select(TravelPlan).where(
                TravelPlan.id == plan_id,
                TravelPlan.user_id == user_id,
            )
        )
        plan = result.scalar_one_or_none()
        if not plan:
            return TravelAgentResult(
                response="抱歉，未找到该行程或无权限修改。请确认行程归属后再试。",
                travel_plan=None,
            )

    import asyncio
    from sqlalchemy import select

    # Try local patch first — skip heavy data fetching for small edits
    patched = await _patch_itinerary(instruction, current_itinerary)
    if patched is not None:
        excluded_pois = _infer_excluded_pois(instruction, current_itinerary)
        requested_pois = _infer_requested_pois(instruction)
        if requested_pois:
            _ensure_requested_pois(patched, requested_pois, instruction)
        summary = await _generate_summary(destination, days, patched, [], {})
        return TravelAgentResult(
            response=f"已根据你的反馈「{instruction}」调整了行程。\n\n{summary}",
            travel_plan=TravelPlanArtifact(
                destination=destination,
                days=days,
                itinerary=patched,
                preferences={},
            ),
        )

    async def safe_call(coro, name: str, default=None):
        try:
            return await coro
        except Exception as e:
            logger.warning("%s failed: %s", name, e)
            return default or []

    pois_task = safe_call(search_scenic_spots(db, destination, limit=20), "scenic_spots")
    restaurants_task = safe_call(search_restaurants(db, destination, limit=10), "restaurants")
    weather_task = safe_call(get_weather_forecast(destination, days=days), "weather")

    async def fetch_products():
        try:
            result = await db.execute(
                select(Product).where(Product.status == "active").order_by(Product.rating.desc()).limit(10)
            )
            return [{"id": p.id, "name": p.name, "price": p.price, "tags": p.tags or []} for p in result.scalars().all()]
        except Exception as e:
            logger.warning("fetch_products failed: %s", e)
            return []

    pois, restaurants, weather, products = await asyncio.gather(
        pois_task, restaurants_task, weather_task, fetch_products(),
    )

    excluded_pois = _infer_excluded_pois(instruction, current_itinerary)
    replacement_pois = _exclude_pois(pois, excluded_pois)

    prompt = _build_adjustment_prompt(instruction, current_itinerary, replacement_pois, restaurants, weather, products)

    try:
        itinerary = await asyncio.wait_for(
            llm_service.extract_json(
                system_prompt=TRAVEL_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            ),
            timeout=60,
        )
    except Exception as e:
        logger.warning("adjust_plan JSON generation failed: %s", e)
        itinerary = _fallback_itinerary(destination, days, replacement_pois)
        itinerary["theme"] = f"{destination}调整后行程"

    if not isinstance(itinerary, dict) or not itinerary.get("day_by_day"):
        itinerary = _fallback_itinerary(destination, days, replacement_pois)
        itinerary["theme"] = f"{destination}调整后行程"

    if excluded_pois and _itinerary_contains_pois(itinerary, excluded_pois):
        _replace_excluded_activities(itinerary, replacement_pois, excluded_pois)

    requested_pois = _infer_requested_pois(instruction)
    if requested_pois:
        _ensure_requested_pois(itinerary, requested_pois, instruction)

    _merge_weather_into_itinerary(itinerary, weather)

    requested_note = ""
    if requested_pois:
        requested_note = f"已将 {', '.join(requested_pois)} 同步到行程卡。\n\n"

    summary = f"已根据你的反馈「{instruction}」调整了行程。\n\n{requested_note}"

    summary += await _generate_summary(destination, days, itinerary, weather, {})

    return TravelAgentResult(
        response=summary,
        travel_plan=TravelPlanArtifact(
            destination=destination,
            days=days,
            itinerary=itinerary,
            preferences={},
        ),
    )


async def _generate_summary(
    destination: str,
    days: int,
    itinerary: dict,
    weather: list[dict],
    preferences: dict,
) -> str:
    """Generate a human-readable summary of the itinerary."""
    prompt = f"""你是一个热情的旅行规划师。请为以下行程生成一段自然流畅的推荐语（约 200-300 字），
用中文回复，语气热情专业。概括行程亮点、特色推荐和实用建议：

## 目的地: {destination}
## 天数: {days}天
## 行程: {json.dumps(itinerary, ensure_ascii=False)}
## 天气: {json.dumps(weather, ensure_ascii=False)}

请简要介绍整体行程并突出亮点。
"""

    summary = await llm_service.chat(
        system_prompt="你是一个热情的旅行规划师，用中文回复。",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=800,
        temperature=0.7,
    )
    return summary


def _normalize_poi_name(name: str) -> str:
    """Normalize POI names for lightweight matching."""
    return re.sub(r"[\s\-·・—_()（）《》【】\[\]]+", "", name or "").lower()


def _poi_aliases(name: str) -> set[str]:
    normalized = _normalize_poi_name(name)
    aliases = {normalized}
    for suffix in ("博物院", "博物馆", "公园", "广场", "景区", "街区", "大街", "寺"):
        if normalized.endswith(suffix):
            aliases.add(normalized[: -len(suffix)])
    return {alias for alias in aliases if alias}


def _collect_activity_pois(itinerary: dict) -> list[str]:
    pois: list[str] = []
    for day in itinerary.get("day_by_day", []) or []:
        for activity in day.get("activities", []) or []:
            poi = activity.get("poi")
            if isinstance(poi, str) and poi:
                pois.append(poi)
    return pois




def _infer_requested_pois(instruction: str) -> list[str]:
    """Extract POIs the user explicitly asks to include in the itinerary."""
    patterns = [
        r"([一-鿿]{2,6}?)([一-鿿A-Za-z0-9·・]{2,20})(?:一日游|二日游|三日游|\d日游|游玩|旅行|旅游|攻略)",
        r"(?:我想去|想去|想加|加上|加入|加一个|补一个|安排|增加|顺路去|再去|还想去|一定要去|改去)\s*([一-鿿A-Za-z0-9·・、和与及\s]{2,40})",
        r"(?:把|将).{1,30}(?:换成|改成|替换成)\s*([一-鿿A-Za-z0-9·・、和与及\s]{2,40})",
        r"(?:上午|下午|晚上|中午|早上|第二天|第2天|第一天|第1天|第三天|第3天).{0,10}(?:去|安排|加上)\s*([一-鿿A-Za-z0-9·・、和与及\s]{2,40})",
    ]
    pois: list[str] = []
    stop_words = (
        "一下", "一些", "一点", "那里", "这里", "这个", "那个", "吧", "看看",
        "逛逛", "玩玩", "游玩", "玩", "一趟", "附近", "周边", "可以吗", "行吗",
    )
    for pattern in patterns:
        for match in re.finditer(pattern, instruction):
            raw = match.group(match.lastindex or 1)
            raw = re.split(r"[，。,.!！?？；;]|然后|再|顺便|但是|不过", raw)[0]
            parts = re.split(r"[、/]|和|与|及|\s+", raw)
            for part in parts:
                name = part.strip("，。,.!！?？ ")
                for stop in stop_words:
                    if name.endswith(stop):
                        name = name[: -len(stop)]
                if name and len(name) >= 2 and name not in pois:
                    pois.append(name)
    return pois


def _infer_target_day_index(instruction: str, day_count: int) -> int:
    day_map = {
        "第一天": 0,
        "第1天": 0,
        "第二天": 1,
        "第2天": 1,
        "第三天": 2,
        "第3天": 2,
        "第四天": 3,
        "第4天": 3,
        "第五天": 4,
        "第5天": 4,
    }
    for marker, index in day_map.items():
        if marker in instruction and index < day_count:
            return index
    return 0


def _infer_time_slots(instruction: str, count: int) -> list[str]:
    slots = []
    for marker in ("上午", "中午", "下午", "晚上"):
        if marker in instruction:
            slots.append(marker)
    default_slots = ["上午", "下午", "晚上"]
    while len(slots) < count:
        slots.append(default_slots[len(slots) % len(default_slots)])
    return slots[:count]


def _ensure_requested_pois(itinerary: dict, requested_pois: list[str], instruction: str) -> None:
    """Force explicitly requested POIs into structured activities."""
    day_by_day = itinerary.setdefault("day_by_day", [])
    if not day_by_day:
        day_by_day.append({"day": 1, "theme": "按需调整", "activities": []})

    existing = {_normalize_poi_name(poi) for poi in _collect_activity_pois(itinerary)}
    target_day = day_by_day[_infer_target_day_index(instruction, len(day_by_day))]
    activities = target_day.setdefault("activities", [])
    time_slots = _infer_time_slots(instruction, len(requested_pois))
    insert_at = 0

    for index, poi in enumerate(requested_pois):
        normalized = _normalize_poi_name(poi)
        if not normalized or normalized in existing:
            continue

        new_activity = {
            "time": time_slots[index],
            "poi": poi,
            "duration": "2小时",
            "description": f"根据你的要求安排{poi}",
            "tips": "这是你在对话中点名想去的地点，已同步到行程卡。",
        }

        if insert_at < len(activities):
            activities[insert_at] = new_activity
        else:
            activities.append(new_activity)
        insert_at += 1
        existing.add(normalized)

    if requested_pois:
        target_day["theme"] = f"{requested_pois[0]}主题探索"
        itinerary["theme"] = f"围绕{requested_pois[0]}调整后的行程"



def _infer_excluded_pois(instruction: str, current_itinerary: dict) -> list[str]:
    """Infer POIs the user wants to avoid from the adjustment instruction."""
    current_pois = _collect_activity_pois(current_itinerary)
    if not current_pois:
        return []

    normalized_instruction = _normalize_poi_name(instruction)
    replace_all_markers = (
        "这几个", "这些", "全部", "全都", "都玩过", "都去过",
        "都打卡", "经典景点", "换别的", "换成别的",
    )
    if any(marker in instruction for marker in replace_all_markers):
        return current_pois

    excluded: list[str] = []
    for poi in current_pois:
        if any(alias and alias in normalized_instruction for alias in _poi_aliases(poi)):
            excluded.append(poi)
    return excluded


def _exclude_pois(pois: list[dict], excluded_names: list[str]) -> list[dict]:
    if not excluded_names:
        return pois

    excluded_aliases = set()
    for name in excluded_names:
        excluded_aliases.update(_poi_aliases(name))

    filtered: list[dict] = []
    for poi in pois:
        name = str(poi.get("name", ""))
        aliases = _poi_aliases(name)
        if aliases.isdisjoint(excluded_aliases):
            filtered.append(poi)
    return filtered or pois


def _matches_excluded_poi(name: str, excluded_names: list[str]) -> bool:
    aliases = _poi_aliases(name)
    for excluded in excluded_names:
        excluded_aliases = _poi_aliases(excluded)
        if not aliases.isdisjoint(excluded_aliases):
            return True
    return False


def _itinerary_contains_pois(itinerary: dict, excluded_names: list[str]) -> bool:
    return any(_matches_excluded_poi(poi, excluded_names) for poi in _collect_activity_pois(itinerary))


def _replace_excluded_activities(
    itinerary: dict,
    replacement_pois: list[dict],
    excluded_names: list[str],
) -> None:
    """Replace stale activities in-place when model output did not honor exclusions."""
    candidates = [poi for poi in replacement_pois if not _matches_excluded_poi(str(poi.get("name", "")), excluded_names)]
    if not candidates:
        return

    used = {_normalize_poi_name(poi) for poi in _collect_activity_pois(itinerary)}
    candidate_index = 0

    for day in itinerary.get("day_by_day", []) or []:
        for activity in day.get("activities", []) or []:
            current_name = str(activity.get("poi", ""))
            if not _matches_excluded_poi(current_name, excluded_names):
                continue

            replacement = None
            while candidate_index < len(candidates):
                candidate = candidates[candidate_index]
                candidate_index += 1
                candidate_name = str(candidate.get("name", ""))
                normalized = _normalize_poi_name(candidate_name)
                if normalized and normalized not in used:
                    replacement = candidate
                    used.add(normalized)
                    break

            if not replacement:
                return

            replacement_name = str(replacement.get("name", current_name))
            activity["poi"] = replacement_name
            activity["description"] = f"参观{replacement_name}"


def _looks_like_local_adjustment(instruction: str) -> bool:
    """Detect local edits (time shifts, reordering, minor adds/removals)."""
    local_markers = (
        "上午", "下午", "晚上", "中午",
        "改到", "移到", "挪到", "调到", "调整到",
        "交换", "互换", "对调",
        "提前", "推迟", "延后", "改时间",
        "加一个", "加一项", "加个", "加个活动", "添加",
        "删掉", "删除", "去掉", "移除", "取消",
        "改一下", "修改一下",
    )
    global_markers = (
        "重新规划", "重排", "重新安排", "重做",
        "太赶", "太累", "太紧凑", "太松",
        "预算不足", "预算超", "换个风格",
    )
    if any(marker in instruction for marker in global_markers):
        return False
    return any(marker in instruction for marker in local_markers)


def _build_patch_prompt(instruction: str, current_itinerary: dict) -> str:
    """Build a lightweight prompt for local patch adjustments."""
    itinerary_str = json.dumps(current_itinerary, ensure_ascii=False, indent=2)
    return f"""用户希望对已规划的行程做局部微调，请仅修改指定部分，严格保持其他内容不变。

## 修改要求
{instruction}

## 当前完整行程（JSON）
{itinerary_str}

## 要求
1. 只修改用户明确指定的部分，其余内容（餐厅、酒店、商品推荐等）一律保持原样
2. 保持 JSON 结构与原来完全一致
3. 输出完整的行程 JSON（不要只输出改动部分）

修改后，检查是否所有 days 的 weather 字段都包含 condition、temp_min、temp_max。
"""


async def _patch_itinerary(
    instruction: str,
    current_itinerary: dict,
) -> dict | None:
    """Try a lightweight local patch before falling back to full regeneration.

    Returns the patched itinerary, or None if patching is not applicable.
    """
    if not _looks_like_local_adjustment(instruction):
        return None

    prompt = _build_patch_prompt(instruction, current_itinerary)
    try:
        patched = await llm_service.extract_json(
            system_prompt="你是一个行程微调专家，只修改用户指定的部分，保持其他内容严格不变。",
            messages=[{"role": "user", "content": prompt}],
        )
        if patched and isinstance(patched, dict) and patched.get("day_by_day"):
            return patched
    except Exception as e:
        logger.info("Local patch failed, will fall back to full regeneration: %s", e)

    return None


def _fallback_itinerary(destination: str, days: int, pois: list[dict]) -> dict:
    """Generate a simple itinerary when LLM fails."""
    day_by_day = []
    for d in range(1, days + 1):
        day_pois = pois[(d - 1) * 3: d * 3] if pois else []
        activities = []
        for i, p in enumerate(day_pois):
            activities.append({
                "time": ["上午", "下午", "晚上"][i] if i < 3 else "其他",
                "poi": p.get("name", f"景点{i+1}"),
                "duration": "2小时",
                "description": f"参观{p.get('name', '景点')}",
            })
        day_by_day.append({
            "day": d,
            "theme": f"第{d}天探索",
            "weather": {"condition": "适中"},
            "meals": [
                {"type": "午餐", "recommendation": "品尝当地特色美食", "restaurant": "附近餐厅"},
                {"type": "晚餐", "recommendation": "体验当地美食", "restaurant": "当地特色餐厅"},
            ],
            "activities": activities,
            "shopping": [],
            "hotel": {"name": f"{destination}推荐酒店", "price_level": "舒适", "reason": "地理位置便利，交通方便", "tips": "建议提前预订"},
            "transport_tips": "建议乘坐公共交通",
        })

    return {
        "destination": destination,
        "days": days,
        "theme": f"{destination}{days}日游",
        "day_by_day": day_by_day,
        "budget_estimate": {"total": "待定"},
        "tips": [f"建议提前查看{destination}天气预报", "提前预订住宿可获得更优惠价格"],
    }
