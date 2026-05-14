from __future__ import annotations

from typing import Any


def render_itinerary_summary(destination: str, days: int, itinerary: dict[str, Any]) -> str:
    highlights: list[str] = []
    for day in itinerary.get("day_by_day", []) or []:
        for activity in day.get("activities", []) or []:
            poi = activity.get("poi")
            if poi and poi not in highlights:
                highlights.append(str(poi))
            if len(highlights) >= 4:
                break
        if len(highlights) >= 4:
            break
    budget = (itinerary.get("budget_estimate") or {}).get("total") or "待确认"
    title = "、".join(highlights) if highlights else f"{destination}核心景点"
    return (
        f"已为你生成{destination}{days}日约束优化行程，围绕{title}展开。"
        f"预算预估为{budget}，路线已兼顾兴趣匹配、餐饮安排和交通顺畅度。"
    )
