from __future__ import annotations

import re
from typing import Any


def normalize_name(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"[\s·\-\(\)（）【】\[\]。，“”,.!！?？]", "", value).lower()


def parse_budget(message: str, preferences: dict[str, Any] | None = None) -> float | None:
    preferences = preferences or {}
    explicit = preferences.get("budget")
    if isinstance(explicit, (int, float)):
        return float(explicit)
    patterns = [
        r"(?:预算|控制在|不超过|以内|人均)\s*(\d{2,6})",
        r"(\d{2,6})\s*(?:元|块|预算)",
    ]
    for pattern in patterns:
        match = re.search(pattern, message)
        if match:
            return float(match.group(1))
    return None


def parse_pace(message: str, preferences: dict[str, Any] | None = None) -> str:
    preferences = preferences or {}
    pace = str(preferences.get("pace") or "").lower()
    if pace in {"relaxed", "compact", "balanced"}:
        return pace
    if any(word in message for word in ("轻松", "慢", "不赶", "悠闲")):
        return "relaxed"
    if any(word in message for word in ("紧凑", "多安排", "尽量多", "打卡")):
        return "compact"
    return "balanced"


def parse_constraints(
    message: str,
    preferences: dict[str, Any] | None = None,
    *,
    requested_pois: list[str] | None = None,
    avoid_pois: list[str] | None = None,
) -> dict[str, Any]:
    preferences = preferences or {}
    must_visit = list(dict.fromkeys([*(requested_pois or []), *preferences.get("must_visit", [])]))
    avoid = list(dict.fromkeys([*(avoid_pois or []), *preferences.get("avoid_pois", [])]))
    cuisine = preferences.get("cuisine") or preferences.get("food_preference")
    if any(word in message for word in ("湘菜", "湖南菜")):
        cuisine = "湘菜"
    elif any(word in message for word in ("川菜", "四川菜")):
        cuisine = "川菜"
    elif any(word in message for word in ("本地", "地道", "特色")):
        cuisine = "本地特色"
    return {
        "budget": parse_budget(message, preferences),
        "pace": parse_pace(message, preferences),
        "must_visit": must_visit,
        "avoid_pois": avoid,
        "cuisine": cuisine,
        "transport": preferences.get("transport") or ("公共交通" if "公交" in message or "地铁" in message else "公共交通"),
    }
