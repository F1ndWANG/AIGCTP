"""Prompt builder for Travel Agent — constructs LLM prompts for itinerary generation."""

import json


TRAVEL_SYSTEM_PROMPT = """你是专业的旅行规划师。你的核心能力是根据用户需求、偏好和约束条件，生成高质量、可执行的旅行行程。

## 核心原则
1. **理解意图优先**: 用户说"不想去X"就是真的不想去 — 不要自作主张保留。用户说"想去Y"就要想办法安排进去。
2. **真实性**: 只在行程中包含你确切知道的真实景点、餐厅和酒店。不要编造不存在的景点名称。
3. **地理逻辑**: 同一区域的景点安排在相邻时段，减少不必要的交通时间。
4. **节奏把控**: 每天 3-4 个主要活动，上午/下午各 1-2 个，晚上 1 个轻松活动。
5. **天气适应**: 雨天优先室内（博物馆、购物、美食），晴天优先户外（景区、公园、街区）。
6. **本地特色**: 推荐当地有代表性的餐厅和美食，而非全国连锁店。

## 主题命名规范
- 行程总 theme: 用目的地+亮点概括，如 "京城古韵与胡同漫步"、"西湖茶韵三日慢旅"、"成都火锅与熊猫之旅"
- 每天 theme: 用当天最核心的体验命名，如 "故宫深度探索"、"西湖环湖骑行日"、"太古里潮流美食"
- 绝对禁止: "调整后的行程"、"修改后的行程"、"第X天"、空字符串

## 输出规范
严格按照要求的 JSON 结构输出。所有中文字段使用自然流畅的中文表达。
"""


def _format_poi_list(pois: list[dict], limit: int = 15) -> str:
    lines = []
    for p in pois[:limit]:
        lines.append(f"  - {p.get('name', '?')} ({p.get('category', '')}) rating:{p.get('rating','')} {p.get('address','')[:30]}")
    return "\n".join(lines)


def _format_rest_list(restaurants: list[dict], limit: int = 10) -> str:
    lines = []
    for r in restaurants[:limit]:
        lines.append(f"  - {r.get('name', '?')} ({r.get('category', '')}) rating:{r.get('rating','')}")
    return "\n".join(lines)


def _format_weather_list(weather: list[dict]) -> str:
    lines = [f"  - {w.get('date','')}: {w.get('condition','')} {w.get('temp_min','')}~{w.get('temp_max','')}C" for w in weather]
    return "\n".join(lines) or "  (暂无天气数据)"


def _format_product_list(products: list[dict] | None, limit: int = 10) -> str:
    if not products:
        return "  (暂无商品数据)"
    lines = []
    for p in products[:limit]:
        lines.append(f"  - {p.get('name', '?')}  ${p.get('price',0)} tags:{','.join(p.get('tags', []) or [])[:40]}")
    return "\n".join(lines)


def build_itinerary_prompt(
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
    """Build the prompt for new itinerary generation."""
    poi_str = _format_poi_list(pois)
    rest_str = _format_rest_list(restaurants)
    weather_str = _format_weather_list(weather)
    prod_str = _format_product_list(products)
    pref_str = json.dumps(user_preferences, ensure_ascii=False)

    return f"""规划一个 {destination} 的 {days} 天旅行行程。

## 用户需求
{original_message or f"探索{destination}的精华景点"}

## 用户偏好
{pref_str}

## 可用资源
### 景点
{poi_str or '无预设景点数据，请根据你对' + destination + '的了解推荐真实景点'}

### 餐厅
{rest_str or '无预设餐厅数据，请根据你对' + destination + '的了解推荐本地特色餐厅'}

### 商品
{prod_str}

### 天气
{weather_str}

请生成完整 JSON，结构如下:
{{
  "destination": "{destination}",
  "days": {days},
  "theme": "吸引人的行程主题",
  "day_by_day": [ ... ],
  "budget_estimate": {{ "total": "范围", "breakdown": {{}} }},
  "tips": ["实用建议"]
}}

每天结构: {{"day": N, "theme": "当日主题", "weather": {{"condition": "", "temp_min": "", "temp_max": ""}}, "meals": [餐食], "activities": [活动], "shopping": [商品推荐], "hotel": {{}}, "transport_tips": ""}}

重要:
- theme 要有辨识度，不是"调整后的行程"这种占位符
- 用户点名的景点必须出现在 activities 中
- 推荐真实存在的景点和餐厅，不要编造
- 考虑天气因素安排室内/室外活动
- 每天 3-4 个活动，节奏适中
"""


def build_adjustment_prompt(
    instruction: str,
    current_itinerary: dict,
    pois: list[dict],
    restaurants: list[dict],
    weather: list[dict],
    products: list[dict] | None = None,
    excluded_poi_names: list[str] | None = None,
    requested_poi_names: list[str] | None = None,
) -> str:
    """Build prompt for adjusting an existing itinerary. ALL POIs are passed — LLM decides."""
    itinerary_str = json.dumps(current_itinerary, ensure_ascii=False, indent=2)
    poi_str = json.dumps(pois[:20], ensure_ascii=False, indent=2)
    rest_str = json.dumps(restaurants[:10], ensure_ascii=False, indent=2)
    weather_str = json.dumps(weather, ensure_ascii=False, indent=2)
    prod_str = _format_product_list(products)

    intent_parts = [f"用户需求: {instruction}"]
    if excluded_poi_names:
        intent_parts.append(f"用户不想去: {', '.join(excluded_poi_names)}（行程中不要包含这些地点）")
    if requested_poi_names:
        intent_parts.append(f"用户想去: {', '.join(requested_poi_names)}（请安排到行程中）")
    intent_block = "\n".join(intent_parts)

    return f"""你是专业旅行规划师。用户对已有行程提出了反馈，请根据反馈重新规划完整行程。

{intent_block}

## 参考: 当前行程
{itinerary_str}

## 可用资源
### 景点
{poi_str}

### 餐厅
{rest_str}

### 商品
{prod_str}

### 天气
{weather_str}

## 规划要求
1. **尊重用户意图**:
   - 明确说不去的景点，绝对不能出现在新行程中
   - 说想去的景点，必须安排进去
   - 理解用户的风格偏好（悠闲/紧凑、文化/自然/美食）
2. **重新构思**: 不要机械保留旧行程。根据用户反馈重新思考每天的安排
3. **地理合理**: 相邻景点安排在同一天
4. **天气考量**: 雨天侧重室内，晴天侧重户外
5. **主题命名**: 要有吸引力，反映行程亮点。禁止 "调整后的行程"、"修改后的行程" 等占位词
6. **真实性**: 只推荐真实存在的景点和餐厅

输出完整的 Day-by-Day JSON 结构。
"""


def build_unified_itinerary_prompt(
    destination: str, days: int,
    user_preferences: dict,
    pois: list[dict], restaurants: list[dict],
    hotels: list[dict], weather: list[dict],
    products: list[dict] | None = None,
    original_message: str = "",
    conversation_history: str = "",
    requested_poi_names: list[str] | None = None,
    excluded_poi_names: list[str] | None = None,
) -> str:
    """Build a unified prompt: generates BOTH a chat response and an itinerary JSON in one call."""
    poi_str = _format_poi_list(pois)
    rest_str = _format_rest_list(restaurants)
    weather_str = _format_weather_list(weather)
    prod_str = _format_product_list(products)
    pref_str = json.dumps(user_preferences, ensure_ascii=False)
    conv_ctx = f"\n## 对话上下文\n{conversation_history}\n" if conversation_history else ""
    requested_ctx = f"\n用户提到的景点: {', '.join(requested_poi_names)}\n请理解用户意图，将这些景点合理地安排到行程中。\n" if requested_poi_names else ""
    excluded_ctx = (
        f"\n用户当前会话明确不想去: {', '.join(excluded_poi_names)}\n"
        "这些景点及其高度相关变体绝对不要出现在 activities 中，请补充其他替代景点。\n"
        if excluded_poi_names else ""
    )

    return f"""为用户规划一个 {destination} 的 {days} 天旅行行程。

## 用户需求
{original_message or f"探索{destination}的精华景点"}
{conv_ctx}{requested_ctx}{excluded_ctx}
## 用户偏好
{pref_str}

## 可用资源
### 景点
{poi_str or '无预设数据，请根据你对' + destination + '的了解推荐真实景点'}
### 餐厅
{rest_str or '无预设数据，请根据你对' + destination + '的了解推荐本地特色餐厅'}
### 商品
{prod_str}
### 天气
{weather_str}

## 你的任务
1. **先写一段详细的文字回复**（300-500字）：像热情的旅行规划师一样，介绍此行亮点、每天精彩安排、美食推荐、实用贴士。用自然的中文口语。不要机械罗列景点，而是讲故事般地描述体验。

2. **在回复末尾，附上完整的行程 JSON**（用 ```json 代码块包裹），JSON 结构:
{{"destination":"{destination}","days":{days},"theme":"吸引人的主题","day_by_day":[...],"budget_estimate":{{"total":"范围","breakdown":{{}}}},"tips":["建议1","建议2"]}}

每天: {{"day":N,"theme":"当日主题","weather":{{"condition":"","temp_min":"","temp_max":""}},"meals":[...],"activities":[{{"time":"上午","poi":"景点名","duration":"2小时","description":"描述","tips":"贴士"}}],"shopping":[...],"hotel":{{"name":"","price_level":"","reason":""}},"transport_tips":""}}

要求: theme 有辨识度；景点来自可用列表或你的知识；每天 3-4 个活动；用户点名的必须出现；用户排除的景点及其相关变体绝对不能出现。
"""


def build_unified_adjustment_prompt(
    instruction: str,
    current_itinerary: dict,
    pois: list[dict], restaurants: list[dict],
    weather: list[dict],
    products: list[dict] | None = None,
    excluded_poi_names: list[str] | None = None,
    requested_poi_names: list[str] | None = None,
    conversation_history: str = "",
) -> str:
    """Build a unified adjustment prompt: response + updated itinerary JSON in one call."""
    itinerary_str = json.dumps(current_itinerary, ensure_ascii=False, indent=2)
    poi_str = json.dumps(pois[:20], ensure_ascii=False, indent=2)
    rest_str = json.dumps(restaurants[:10], ensure_ascii=False, indent=2)
    weather_str = json.dumps(weather, ensure_ascii=False, indent=2)
    prod_str = _format_product_list(products)

    intent_parts = [f"用户需求: {instruction}"]
    if excluded_poi_names:
        intent_parts.append(
            f"用户不想去: {', '.join(excluded_poi_names)}"
            "（这些景点及其高度相关变体绝对不要出现在新行程中，必须补充替代景点）"
        )
    if requested_poi_names:
        intent_parts.append(f"用户想去: {', '.join(requested_poi_names)}（必须安排到行程里）")
    intent_block = "\n".join(intent_parts)

    conv_ctx = f"\n{conversation_history}\n" if conversation_history else ""

    return f"""用户对已有行程提出反馈，请根据反馈重新规划。

{intent_block}
{conv_ctx}
## 当前行程参考
{itinerary_str}

## 可用资源
### 景点
{poi_str}
### 餐厅
{rest_str}
### 商品
{prod_str}
### 天气
{weather_str}

## 你的任务
1. **先写一段详细的文字回复**（300-500字）：确认你理解了用户的需求，说明你对行程做了哪些调整，介绍新行程的亮点和特色。用热情自然的中文，像朋友聊天一样。

2. **在回复末尾，附上完整的新行程 JSON**（用 ```json 代码块包裹），结构同标准行程格式。

关键要求: 尊重用户意图（不去的及其相关变体绝对不包含、想去的一定安排）、每天 3-4 个活动、theme 有辨识度；删除景点后必须补充替代景点，不能留下空行程。
"""
