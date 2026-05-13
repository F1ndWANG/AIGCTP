from __future__ import annotations

from typing import Any


def explain_item(item: dict[str, Any], profile: dict[str, Any]) -> str:
    metadata = item.get("metadata") or {}
    scores = item.get("_scores") or {}
    if scores.get("user_affinity", 0) >= 0.55:
        return "结合你最近的浏览和选择记录推荐。"
    if item["domain"] == "commerce":
        tags = metadata.get("tags") or []
        if tags:
            return f"和你关注的 {str(tags[0])} 相关，评分也不错。"
        return "高评分好物，适合作为当前需求的补充。"
    if item["domain"] == "restaurant":
        cuisine = metadata.get("cuisine")
        if cuisine:
            return f"匹配你当前关注的{cuisine}口味。"
        return "根据城市和历史餐厅选择为你排序。"
    if item["domain"] == "travel":
        if item.get("item_type") == "travel_note":
            likes = (metadata.get("like_count") or 0) + (metadata.get("save_count") or 0)
            if likes:
                return "这篇旅行笔记有不错的互动反馈，和你的旅行兴趣相关。"
            return "来自社区分享的旅行笔记，可作为行程灵感参考。"
        city = metadata.get("city")
        if city:
            return f"结合你近期的{city}行程兴趣推荐。"
        return "适合继续完善或复用的行程方案。"
    if item["domain"] == "diet":
        return "根据你的饮食记录和健康偏好推荐。"
    return "来自跨域混合推荐排序结果。"
