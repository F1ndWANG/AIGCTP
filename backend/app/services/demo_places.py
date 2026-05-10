"""Local demo POI data used when third-party map APIs are unavailable."""
from __future__ import annotations

from typing import Optional


_CITY_RESTAURANTS: dict[str, list[dict]] = {
    "北京": [
        {
            "name": "四季民福烤鸭店",
            "address": "北京市东城区灯市口西街",
            "rating": "4.7",
            "category": "北京菜;烤鸭",
            "tags": ["烤鸭", "北京菜", "家庭聚餐"],
            "longitude": 116.4105,
            "latitude": 39.9187,
            "phone": "010-00000000",
            "reason": "经典北京烤鸭，适合作为一日游的正餐体验。",
            "recommended_dishes": ["北京烤鸭", "贝勒烤肉", "炸酱面"],
        },
        {
            "name": "方砖厂69号炸酱面",
            "address": "北京市东城区鼓楼东大街方砖厂胡同",
            "rating": "4.5",
            "category": "北京小吃;面食",
            "tags": ["炸酱面", "胡同", "小吃"],
            "longitude": 116.3972,
            "latitude": 39.9402,
            "phone": "010-00000001",
            "reason": "靠近什刹海和鼓楼，适合午后胡同漫步时顺路用餐。",
            "recommended_dishes": ["老北京炸酱面", "卤煮", "北冰洋"],
        },
        {
            "name": "护国寺小吃",
            "address": "北京市西城区护国寺街",
            "rating": "4.4",
            "category": "北京小吃",
            "tags": ["豆汁", "驴打滚", "小吃"],
            "longitude": 116.3763,
            "latitude": 39.9314,
            "phone": "010-00000002",
            "reason": "北京传统小吃选择多，适合想快速体验本地风味的行程。",
            "recommended_dishes": ["豌豆黄", "焦圈", "面茶"],
        },
        {
            "name": "南门涮肉",
            "address": "北京市东城区天坛路",
            "rating": "4.6",
            "category": "火锅;老北京涮肉",
            "tags": ["涮羊肉", "铜锅", "晚餐"],
            "longitude": 116.4066,
            "latitude": 39.8827,
            "phone": "010-00000003",
            "reason": "天坛附近的老北京铜锅涮肉，适合一天行程结束后补充热量。",
            "recommended_dishes": ["手切羊肉", "麻酱烧饼", "糖蒜"],
        },
    ],
    "成都": [
        {
            "name": "陈麻婆豆腐",
            "address": "成都市青羊区西玉龙街",
            "rating": "4.6",
            "category": "川菜",
            "tags": ["麻婆豆腐", "川菜", "老字号"],
            "longitude": 104.0713,
            "latitude": 30.6741,
            "phone": "028-00000000",
            "reason": "川菜代表性强，适合第一次到成都的正餐选择。",
            "recommended_dishes": ["麻婆豆腐", "回锅肉", "钟水饺"],
        },
        {
            "name": "龙抄手",
            "address": "成都市锦江区春熙路",
            "rating": "4.3",
            "category": "成都小吃",
            "tags": ["抄手", "小吃", "春熙路"],
            "longitude": 104.0817,
            "latitude": 30.6578,
            "phone": "028-00000001",
            "reason": "小吃品类集中，适合逛街途中快速补给。",
            "recommended_dishes": ["红油抄手", "担担面", "赖汤圆"],
        },
    ],
}

_CITY_SCENIC_SPOTS: dict[str, list[dict]] = {
    "北京": [
        {
            "poi_id": "demo-beijing-forbidden-city",
            "name": "故宫博物院",
            "latitude": 39.9163,
            "longitude": 116.3972,
            "category": "风景名胜",
            "address": "北京市东城区景山前街4号",
            "rating": "4.8",
            "tags": ["历史建筑", "博物馆", "北京经典"],
            "image_urls": [],
        },
        {
            "poi_id": "demo-beijing-tiananmen",
            "name": "天安门广场",
            "latitude": 39.9056,
            "longitude": 116.3976,
            "category": "风景名胜",
            "address": "北京市东城区东长安街",
            "rating": "4.7",
            "tags": ["城市地标", "广场", "北京经典"],
            "image_urls": [],
        },
        {
            "poi_id": "demo-beijing-shichahai",
            "name": "什刹海",
            "latitude": 39.9392,
            "longitude": 116.3866,
            "category": "风景名胜",
            "address": "北京市西城区前海西街",
            "rating": "4.6",
            "tags": ["胡同", "湖景", "漫步"],
            "image_urls": [],
        },
        {
            "poi_id": "demo-beijing-temple-of-heaven",
            "name": "天坛公园",
            "latitude": 39.8822,
            "longitude": 116.4066,
            "category": "风景名胜",
            "address": "北京市东城区天坛东路甲1号",
            "rating": "4.7",
            "tags": ["公园", "历史建筑", "北京经典"],
            "image_urls": [],
        },
    ],
    "成都": [
        {
            "poi_id": "demo-chengdu-kuanzhai",
            "name": "宽窄巷子",
            "latitude": 30.6692,
            "longitude": 104.0596,
            "category": "风景名胜",
            "address": "成都市青羊区长顺上街",
            "rating": "4.5",
            "tags": ["街区", "小吃", "文创"],
            "image_urls": [],
        }
    ],
}


def has_real_amap_key(api_key: Optional[str]) -> bool:
    if not api_key:
        return False
    lowered = api_key.lower()
    return not any(marker in lowered for marker in ("your_", "placeholder", "replace-with"))


def demo_restaurants(city: str, cuisine: Optional[str] = None, limit: int = 10) -> list[dict]:
    base = list(_CITY_RESTAURANTS.get(city, []))
    if not base:
        base = [
            {
                "name": f"{city}本地风味餐厅",
                "address": f"{city}核心商圈",
                "rating": "4.5",
                "category": cuisine or "本地菜",
                "tags": [cuisine or "本地菜", "适合旅行", "人气餐厅"],
                "longitude": None,
                "latitude": None,
                "phone": "",
                "reason": "本地演示推荐，用于地图 API 未配置时保证功能可用。",
                "recommended_dishes": ["当地招牌菜", "时令小吃"],
            }
        ]
    if cuisine:
        filtered = [
            item for item in base
            if cuisine in item.get("category", "") or cuisine in item.get("tags", [])
        ]
        if filtered:
            base = filtered
    return base[:limit]


def demo_scenic_spots(city: str, limit: int = 20) -> list[dict]:
    base = list(_CITY_SCENIC_SPOTS.get(city, []))
    if not base:
        base = [
            {
                "poi_id": f"demo-{city}-landmark",
                "name": f"{city}核心景点",
                "latitude": None,
                "longitude": None,
                "category": "风景名胜",
                "address": f"{city}市中心",
                "rating": "4.5",
                "tags": ["城市地标", "旅行推荐"],
                "image_urls": [],
            }
        ]
    return base[:limit]
