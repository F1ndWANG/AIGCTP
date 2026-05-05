"""
Restaurant Agent - 餐厅推荐助手

Recommends restaurants based on city, preferences, location, and dietary restrictions.
Leverages existing Amap search_restaurants and search_around APIs.
"""
import json
from typing import Any, Optional

from app.services.llm import llm_service
from app.services.amap import amap_service
from app.core.logging import get_logger

logger = get_logger(__name__)

RESTAURANT_SYSTEM_PROMPT = """你是 AI 生活推荐系统的美食推荐专家。你擅长根据用户的位置、口味偏好和饮食限制推荐餐厅。

## 你的角色
- 你是一个热情、专业的美食达人
- 你会考虑用户的位置、口味偏好、饮食限制
- 你会推荐具体的餐厅，说明推荐理由
- 你会给出实用的建议（人均消费、特色菜品、营业时间等）

## 推荐原则
1. **相关性**: 根据用户的位置和口味推荐
2. **多样性**: 推荐不同类型和价位的选择
3. **实用性**: 给出具体地址、推荐菜品等实用信息
4. **个性化**: 考虑饮食限制和偏好
"""


async def recommend_restaurants(
    city: str,
    user_message: str,
    dietary_restrictions: list[str] | None = None,
    cuisine: str | None = None,
) -> dict[str, Any]:
    """Recommend restaurants in a city based on preferences.

    Returns:
        dict with keys: response (str), restaurants (list)
    """
    # Step 1: Get restaurants from Amap
    try:
        restaurants = await amap_service.search_restaurants(city, keywords=cuisine or None, page_size=20)
    except Exception as e:
        logger.warning("Amap search_restaurants failed: %s", e)
        restaurants = []

    if not restaurants:
        return {
            "response": f"抱歉，目前没有找到{city}的餐厅推荐。请换个关键词试试！",
            "restaurants": [],
            "city": city,
        }

    # Step 2: Filter and rank via LLM
    rest_str = json.dumps(restaurants, ensure_ascii=False, indent=2)
    diet_str = ", ".join(dietary_restrictions) if dietary_restrictions else "无特殊限制"

    ranking_prompt = f"""根据用户请求，从以下餐厅列表中选择最适合的推荐，并生成推荐理由。

## 用户请求
{user_message}

## 所在城市
{city}

## 饮食限制
{diet_str}

## 可用餐厅列表
{rest_str}

## 输出格式
```json
{{
  "response": "给用户的热情推荐语，包含整体推荐理由和亮点",
  "top_picks": [
    {{
      "name": "餐厅名",
      "reason": "推荐理由",
      "recommended_dishes": ["推荐菜品1", "推荐菜品2"],
      "rating_info": "评分和口碑说明"
    }}
  ]
}}
```

选择 3-5 家最合适的餐厅，按推荐优先级排序。
"""

    try:
        ranking = await llm_service.extract_json(
            system_prompt=RESTAURANT_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": ranking_prompt}],
        )
    except Exception as e:
        logger.warning("Restaurant ranking failed: %s", e)
        return {
            "response": f"以下是{city}的部分餐厅推荐，您可以进一步告诉我您的口味偏好来获取更精准的推荐。",
            "restaurants": restaurants[:5],
            "city": city,
        }

    # Build final result
    top_picks = ranking.get("top_picks", [])
    response_text = ranking.get("response", f"为您推荐以下{city}的餐厅：")

    # Enrich top picks with full restaurant data from Amap results
    enriched = []
    for pick in top_picks[:5]:
        name = pick.get("name", "")
        # Match by name similarity
        match = next(
            (r for r in restaurants if r.get("name") == name or name in r.get("name", "")),
            None,
        )
        if match:
            enriched.append({**match, **pick})
        else:
            enriched.append({
                "name": name,
                "reason": pick.get("reason", ""),
                "recommended_dishes": pick.get("recommended_dishes", []),
                "rating_info": pick.get("rating_info", ""),
                "address": "",
            })

    return {
        "response": response_text,
        "restaurants": enriched or restaurants[:5],
        "city": city,
    }


async def recommend_nearby(
    latitude: float,
    longitude: float,
    user_message: str,
    radius: int = 1000,
    types: str | None = None,
) -> dict[str, Any]:
    """Recommend restaurants near a specific location.

    Returns:
        dict with keys: response (str), restaurants (list)
    """
    try:
        restaurants = await amap_service.search_around(
            longitude=longitude,
            latitude=latitude,
            radius=radius,
            types=types or "餐饮服务",
            page_size=20,
        )
    except Exception as e:
        logger.warning("Amap search_around failed: %s", e)
        restaurants = []

    if not restaurants:
        return {
            "response": "附近没有找到餐厅，请扩大搜索范围试试！",
            "restaurants": [],
        }

    rest_str = json.dumps(restaurants, ensure_ascii=False, indent=2)

    prompt = f"""根据用户请求，从以下附近餐厅中选择最适合的推荐。

## 用户请求
{user_message}

## 附近餐厅
{rest_str}

## 输出格式
```json
{{
  "response": "给用户的热情推荐语",
  "top_picks": [
    {{
      "name": "餐厅名",
      "reason": "推荐理由",
      "recommended_dishes": ["推荐菜品1"]
    }}
  ]
}}
```

选择 3-5 家最合适的，按距离和评分综合考虑。
"""

    try:
        ranking = await llm_service.extract_json(
            system_prompt=RESTAURANT_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
    except Exception as e:
        logger.warning("Nearby ranking failed: %s", e)
        return {
            "response": "以下是附近的部分餐厅推荐：",
            "restaurants": restaurants[:5],
        }

    top_picks = ranking.get("top_picks", [])
    enriched = []
    for pick in top_picks[:5]:
        name = pick.get("name", "")
        match = next(
            (r for r in restaurants if r.get("name") == name or name in r.get("name", "")),
            None,
        )
        enriched.append({**match, **pick} if match else {
            "name": name, "reason": pick.get("reason", ""),
            "address": "", "distance": "",
        })

    return {
        "response": ranking.get("response", "以下是为您推荐的附近餐厅："),
        "restaurants": enriched or restaurants[:5],
    }
