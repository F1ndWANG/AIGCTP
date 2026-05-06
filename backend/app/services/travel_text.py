"""Deterministic text extraction helpers for travel-oriented routing."""
from __future__ import annotations

import re

from app.services.llm import llm_service

DEFAULT_CITY = "成都"
KNOWN_CITIES = (
    "北京", "上海", "广州", "深圳", "成都", "重庆", "杭州", "西安",
    "南京", "武汉", "长沙", "厦门", "苏州", "天津", "青岛",
    "大理", "丽江", "昆明", "三亚", "桂林", "洛阳", "开封",
)


def general_chat_system_prompt() -> str:
    return """你是 AI 生活推荐系统的智能助手。你可以帮助用户：
1. 规划旅行行程，并根据目的地、天数和偏好给出建议
2. 推荐饮食和健康方案，包括吃什么、记录饮食、分析营养
3. 推荐餐厅与本地美食
4. 推荐商品和购物方案，包括加购和复购

请使用自然、热情、专业的中文回复。
如果用户提到旅行相关内容，请主动确认是否需要规划行程。"""


def extract_destination(text: str) -> str:
    city_positions = [(text.find(city), city) for city in KNOWN_CITIES if city in text]
    city_positions = [item for item in city_positions if item[0] >= 0]
    if city_positions:
        city_positions.sort(key=lambda item: item[0])
        return city_positions[0][1]

    city_with_poi = re.search(
        r"([一-鿿]{2,6}?)(?:的)?([一-鿿A-Za-z0-9··]{2,20})(?:一日游|二日游|三日游|\d日游|游玩|旅行|旅游|攻略)",
        text,
    )
    if city_with_poi:
        city = city_with_poi.group(1)
        poi = city_with_poi.group(2)
        if city in KNOWN_CITIES:
            return city
        if len(city) <= 3 and len(poi) >= 2:
            return city

    patterns = [
        r"(?:去|到|在|规划|推荐|来)\s*([一-鿿]{2,6}?)(?:[的游玩旅游旅行]|\d+日)",
        r"([一-鿿]{2,6})(?:一日游|二日游|三日游|多日游|\d日游)",
        r"一日游\s*([一-鿿]{2,6})",
        r"([一-鿿]{2,6}?)(?:旅游|旅行|攻略|游玩)",
        r"([一-鿿]{2,6})(?:有什么好吃的|美食|餐厅|饭店|餐馆)",
        r"([一-鿿]{2,6})(?:有什么好玩|景点)",
        r"(?:推荐|想去|了解|说说|问问)\s*([一-鿿]{2,6})",
        r"([一-鿿]{2,6})\s*(?:推荐|景点|好玩|攻略|值得去|天气预报)",
        r"^([一-鿿]{2,4})$",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            dest = match.group(1)
            for prefix in ("去", "到", "来", "在"):
                if dest.startswith(prefix):
                    dest = dest[len(prefix):]
                    break
            return dest
    return DEFAULT_CITY


def extract_days(text: str) -> int:
    digit_match = re.search(r"(\d+)\s*[天日]", text)
    if digit_match:
        return int(digit_match.group(1))

    cn_map = {"一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
    cn_match = re.search(r"([一二两三四五六七八九])\s*[天日]", text)
    if cn_match:
        return cn_map.get(cn_match.group(1), 0)
    return 0


def extract_destination_from_messages(messages: list[dict]) -> str | None:
    for message in reversed(messages):
        content = message.get("content", "")
        if not content:
            continue
        dest = extract_destination(content)
        if dest and dest != DEFAULT_CITY:
            return dest
    return None


async def llm_extract_destination(user_message: str, messages: list[dict]) -> str | None:
    recent = messages[-6:]
    context_lines = []
    for message in recent:
        role = "用户" if message.get("role") == "user" else "AI"
        content = (message.get("content") or "")[:300]
        context_lines.append(f"{role}: {content}")
    context_str = "\n".join(context_lines)

    prompt = f"""用户正在更新行程。
请从最近的对话中提取用户现在最想去的目的地城市或景点。
只返回目的地名称，不要返回其他文字；如果无法确定，就返回 null。

最近对话：
{context_str}

当前用户消息：
{user_message}"""

    try:
        resp = await llm_service.chat(
            system_prompt="你是一个旅行意图分析助手。",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=30,
            temperature=0.1,
        )
        resp = resp.strip().strip('"').strip("'").strip("。")
        if resp and resp != "null" and len(resp) <= 10:
            return resp
    except Exception:
        pass
    return None
