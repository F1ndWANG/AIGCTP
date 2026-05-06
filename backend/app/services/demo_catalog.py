from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.commerce import Category, Product


CATEGORIES = [
    {"name": "旅行好物", "description": "出行装备、收纳、防晒和随身用品", "icon": "🎒", "sort_order": 1},
    {"name": "地方特产", "description": "城市伴手礼、零食茶饮和纪念品", "icon": "🎁", "sort_order": 2},
    {"name": "饮食健康", "description": "健康食品、营养补给和轻食用品", "icon": "🥗", "sort_order": 3},
    {"name": "日常购物", "description": "家居日用、数码小件和生活用品", "icon": "🛒", "sort_order": 4},
    {"name": "AI 推荐", "description": "由 AI 对话生成的个性化商品", "icon": "✨", "sort_order": 99},
]

PRODUCTS = [
    {"name": "轻量折叠双肩包", "price": 89.0, "category": "旅行好物", "stock": 120, "unit": "个", "description": "轻便防泼水，可折叠收纳，适合一日游和城市漫步。", "rating": 4.7, "tags": ["旅行", "背包", "收纳"]},
    {"name": "便携防晒霜 SPF50+", "price": 59.9, "category": "旅行好物", "stock": 160, "unit": "瓶", "description": "清爽不黏腻，适合户外游览和日常通勤。", "rating": 4.6, "tags": ["旅行", "防晒", "护肤"]},
    {"name": "真空压缩收纳袋套装", "price": 35.9, "category": "旅行好物", "stock": 200, "unit": "套", "description": "节省行李空间，适合多日旅行衣物分类。", "rating": 4.5, "tags": ["旅行", "收纳", "行李"]},
    {"name": "便携保温水杯 500ml", "price": 69.9, "category": "旅行好物", "stock": 140, "unit": "个", "description": "不锈钢内胆，长效保温，适合行程补水。", "rating": 4.8, "tags": ["旅行", "水杯", "户外"]},
    {"name": "城市明信片纪念套装", "price": 29.9, "category": "地方特产", "stock": 180, "unit": "套", "description": "城市地标插画明信片，适合旅行纪念和赠友。", "rating": 4.4, "tags": ["纪念品", "旅行", "文创"]},
    {"name": "地方糕点伴手礼盒", "price": 79.0, "category": "地方特产", "stock": 90, "unit": "盒", "description": "精选地方风味点心，适合旅途分享。", "rating": 4.6, "tags": ["特产", "伴手礼", "食品"]},
    {"name": "龙井茶叶便携装", "price": 49.9, "category": "地方特产", "stock": 110, "unit": "盒", "description": "独立小袋包装，适合办公室和旅行携带。", "rating": 4.7, "tags": ["茶叶", "特产", "礼品"]},
    {"name": "每日坚果能量包", "price": 39.9, "category": "饮食健康", "stock": 220, "unit": "盒", "description": "坚果与果干混合，适合作为控糖加餐。", "rating": 4.6, "tags": ["健康", "坚果", "加餐"]},
    {"name": "高蛋白燕麦杯", "price": 42.9, "category": "饮食健康", "stock": 130, "unit": "箱", "description": "即冲即食，适合早餐和健身后补给。", "rating": 4.5, "tags": ["饮食", "高蛋白", "早餐"]},
    {"name": "低脂鸡胸肉即食装", "price": 58.0, "category": "饮食健康", "stock": 100, "unit": "盒", "description": "低脂高蛋白，适合减脂和控卡饮食。", "rating": 4.5, "tags": ["减脂", "蛋白质", "轻食"]},
    {"name": "蓝牙降噪耳机", "price": 299.0, "category": "日常购物", "stock": 80, "unit": "副", "description": "通勤和旅行降噪，续航稳定。", "rating": 4.7, "tags": ["数码", "耳机", "旅行"]},
    {"name": "桌面小风扇充电式", "price": 49.9, "category": "日常购物", "stock": 150, "unit": "台", "description": "三档风速，适合夏季办公和宿舍使用。", "rating": 4.3, "tags": ["风扇", "日用", "夏季"]},
]


async def ensure_demo_catalog(db: AsyncSession) -> None:
    """Create a small demo catalog when the product table is empty."""
    product_count = await db.scalar(select(func.count()).select_from(Product))
    if product_count:
        return

    category_ids: dict[str, int] = {}
    for data in CATEGORIES:
        result = await db.execute(select(Category).where(Category.name == data["name"]))
        category = result.scalar_one_or_none()
        if not category:
            category = Category(**data)
            db.add(category)
            await db.flush()
        category_ids[data["name"]] = category.id

    for data in PRODUCTS:
        payload = dict(data)
        category_name = payload.pop("category")
        db.add(Product(
            **payload,
            category_id=category_ids.get(category_name),
            image_urls=[],
            specs=[],
            source="seed",
        ))

    await db.commit()
