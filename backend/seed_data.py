"""Seed data script — creates demo categories, products, and a demo account.

Usage:
    python seed_data.py

Requires DB to be initialized (tables created). Safe to re-run (idempotent).
"""
import asyncio

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.core.config import settings
from app.core.database import Base
from app.core.security import hash_password
from app.models.user import User
from app.models.commerce import Category, Product

# ── Data ──

CATEGORIES = [
    {"name": "食品饮料", "description": "零食、饮料、粮油调味", "icon": "🍜", "sort_order": 1},
    {"name": "生鲜水果", "description": "水果、蔬菜、肉禽蛋奶", "icon": "🥩", "sort_order": 2},
    {"name": "家居日用", "description": "厨具、收纳、清洁用品", "icon": "🏠", "sort_order": 3},
    {"name": "数码家电", "description": "手机、电脑、小家电", "icon": "📱", "sort_order": 4},
    {"name": "运动户外", "description": "运动鞋服、健身器材", "icon": "🏃", "sort_order": 5},
    {"name": "个护美妆", "description": "护肤品、化妆品、个人护理", "icon": "💄", "sort_order": 6},
]

PRODUCTS = [
    # 食品饮料
    {"name": "有机五常大米 5kg", "price": 49.9, "category": "食品饮料", "stock": 200, "unit": "袋",
     "description": "东北五常有机稻花香大米，颗粒饱满，口感软糯", "rating": 4.8, "tags": ["大米", "主食", "有机"]},
    {"name": "特级初榨橄榄油 750ml", "price": 89.9, "category": "食品饮料", "stock": 150, "unit": "瓶",
     "description": "西班牙进口特级初榨橄榄油，适合凉拌和烹饪", "rating": 4.7, "tags": ["食用油", "橄榄油", "进口"]},
    {"name": "每日坚果混合装 30包", "price": 69.9, "category": "食品饮料", "stock": 300, "unit": "盒",
     "description": "每日坚果混合装，含核桃、腰果、杏仁等多种坚果", "rating": 4.6, "tags": ["坚果", "零食", "健康"]},
    {"name": "纯牛奶 250ml×24盒", "price": 59.9, "category": "食品饮料", "stock": 180, "unit": "箱",
     "description": "100%生牛乳，优质蛋白，家庭装", "rating": 4.9, "tags": ["牛奶", "乳制品", "早餐"]},
    {"name": "龙井茶叶礼盒 250g", "price": 128, "category": "食品饮料", "stock": 50, "unit": "盒",
     "description": "明前特级龙井，西湖核心产区，送礼自用皆宜", "rating": 4.9, "tags": ["茶叶", "龙井", "礼品"]},
    {"name": "黑巧克力 72%可可 礼盒装", "price": 45.9, "category": "食品饮料", "stock": 120, "unit": "盒",
     "description": "比利时工艺黑巧克力，低糖更健康", "rating": 4.5, "tags": ["巧克力", "零食", "进口"]},
    # 生鲜水果
    {"name": "进口红心火龙果 5斤", "price": 39.9, "category": "生鲜水果", "stock": 80, "unit": "箱",
     "description": "越南进口红心火龙果，香甜多汁", "rating": 4.5, "tags": ["水果", "火龙果", "进口"]},
    {"name": "精选鸡蛋 30枚装", "price": 29.9, "category": "生鲜水果", "stock": 200, "unit": "板",
     "description": "散养土鸡蛋，营养丰富，适合家庭", "rating": 4.8, "tags": ["鸡蛋", "蛋类", "早餐"]},
    {"name": "有机西兰花 500g×2", "price": 15.9, "category": "生鲜水果", "stock": 120, "unit": "份",
     "description": "有机种植西兰花，新鲜采摘，富含维生素", "rating": 4.4, "tags": ["蔬菜", "有机", "健康"]},
    {"name": "国产阳光玫瑰葡萄 2斤", "price": 35.9, "category": "生鲜水果", "stock": 60, "unit": "串",
     "description": "颗粒饱满，甜度高，自营冷链配送", "rating": 4.7, "tags": ["水果", "葡萄", "时令"]},
    {"name": "进口三文鱼排 300g", "price": 59.9, "category": "生鲜水果", "stock": 40, "unit": "份",
     "description": "挪威进口三文鱼，刺身级品质，冷链直达", "rating": 4.8, "tags": ["海鲜", "三文鱼", "进口"]},
    # 家居日用
    {"name": "不锈钢保温杯 350ml", "price": 69.9, "category": "家居日用", "stock": 200, "unit": "个",
     "description": "316不锈钢内胆，6小时保温，简约设计", "rating": 4.6, "tags": ["水杯", "保温", "日用"]},
    {"name": "厨房刀具套装 5件套", "price": 129, "category": "家居日用", "stock": 50, "unit": "套",
     "description": "德国不锈钢刀刃，人体工学手柄，含刀架", "rating": 4.5, "tags": ["刀具", "厨房", "厨具"]},
    {"name": "真空压缩袋 4件套", "price": 29.9, "category": "家居日用", "stock": 300, "unit": "套",
     "description": "手卷式免泵，节省收纳空间，旅行必备", "rating": 4.3, "tags": ["收纳", "旅行", "日用"]},
    {"name": "智能感应垃圾桶 12L", "price": 89.9, "category": "家居日用", "stock": 40, "unit": "个",
     "description": "红外感应开盖，静音缓降，IPX5防水", "rating": 4.4, "tags": ["垃圾桶", "智能", "家居"]},
    # 数码家电
    {"name": "蓝牙降噪耳机", "price": 399, "original_price": 499, "category": "数码家电", "stock": 45, "unit": "副",
     "description": "主动降噪，30小时续航，IPX5防水", "rating": 4.7, "tags": ["耳机", "数码", "蓝牙"]},
    {"name": "智能体脂秤", "price": 89.9, "category": "数码家电", "stock": 70, "unit": "台",
     "description": "蓝牙连接APP，测量体脂/水分/肌肉等15项数据", "rating": 4.4, "tags": ["体脂秤", "健康", "智能"]},
    {"name": "桌面小风扇 充电式", "price": 59.9, "category": "数码家电", "stock": 100, "unit": "台",
     "description": "USB充电，3档风速，静音设计", "rating": 4.3, "tags": ["风扇", "桌面", "夏日"]},
    {"name": "便携蓝牙音箱", "price": 149, "category": "数码家电", "stock": 55, "unit": "个",
     "description": "IPX7防水，12小时续航，TWS串联", "rating": 4.6, "tags": ["音箱", "蓝牙", "户外"]},
    # 运动户外
    {"name": "轻量跑步鞋", "price": 299, "original_price": 399, "category": "运动户外", "stock": 60, "unit": "双",
     "description": "透气飞织鞋面，缓震中底，适合日常跑步训练", "rating": 4.6, "tags": ["运动鞋", "跑步", "运动"]},
    {"name": "瑜伽垫 6mm加厚", "price": 79.9, "category": "运动户外", "stock": 90, "unit": "张",
     "description": "TPE环保材质，双面防滑，附带收纳绑带", "rating": 4.5, "tags": ["瑜伽", "健身", "运动"]},
    {"name": "保温运动水壶 500ml", "price": 49.9, "category": "运动户外", "stock": 150, "unit": "个",
     "description": "304不锈钢内胆，12小时保温，防漏设计", "rating": 4.7, "tags": ["水壶", "运动", "户外"]},
    {"name": "跳绳计数跳绳", "price": 25.9, "category": "运动户外", "stock": 200, "unit": "根",
     "description": "电子计数，PVC钢丝绳，长度可调", "rating": 4.4, "tags": ["跳绳", "健身", "运动"]},
    {"name": "速干运动T恤", "price": 89.9, "category": "运动户外", "stock": 100, "unit": "件",
     "description": "吸湿排汗，四面弹力，亲肤透气", "rating": 4.5, "tags": ["运动服", "速干", "跑步"]},
    # 个护美妆
    {"name": "氨基酸洗面奶 120g", "price": 39.9, "category": "个护美妆", "stock": 150, "unit": "支",
     "description": "温和氨基酸配方，不紧绷，适合所有肤质", "rating": 4.7, "tags": ["洁面", "护肤", "氨基酸"]},
    {"name": "防晒霜 SPF50+ 60ml", "price": 79.9, "category": "个护美妆", "stock": 100, "unit": "瓶",
     "description": "物理+化学双重防晒，清爽不油腻", "rating": 4.6, "tags": ["防晒", "护肤", "夏日"]},
    {"name": "护手霜套装 3支装", "price": 29.9, "category": "个护美妆", "stock": 200, "unit": "盒",
     "description": "乳木果+橄榄+玫瑰三款，滋润保湿", "rating": 4.4, "tags": ["护手霜", "护肤", "冬季"]},
    {"name": "电动牙刷 声波式", "price": 169, "category": "个护美妆", "stock": 60, "unit": "支",
     "description": "IPX7防水，5种清洁模式，含4支刷头", "rating": 4.8, "tags": ["牙刷", "电动", "个护"]},
]


async def seed_database():
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    db = async_session()
    try:
        # ── 1. Demo account ──
        result = await db.execute(select(User).where(User.username == "demo"))
        existing = result.scalar_one_or_none()
        if not existing:
            demo = User(
                username="demo",
                hashed_password=hash_password("demo123"),
                display_name="演示用户",
                preferences={"theme": "light", "language": "zh"},
            )
            db.add(demo)
            await db.commit()
            await db.refresh(demo)
            print("[OK] Demo account created: demo / demo123")
        else:
            print("[SKIP] Demo account already exists")

        # ── 2. Categories ──
        cat_map = {}
        for c in CATEGORIES:
            result = await db.execute(select(Category).where(Category.name == c["name"]))
            existing = result.scalar_one_or_none()
            if not existing:
                cat = Category(**c)
                db.add(cat)
                await db.flush()
                cat_map[c["name"]] = cat.id
                print(f"[OK] Category created: {c['name']}")
            else:
                cat_map[c["name"]] = existing.id

        # ── 3. Products ──
        count = 0
        for p in PRODUCTS:
            product_data = dict(p)
            cat_name = product_data.pop("category")
            category_id = cat_map.get(cat_name)
            if category_id is None:
                print(f"[WARN] Skip product {product_data['name']}: category {cat_name} not found")
                continue

            result = await db.execute(select(Product).where(Product.name == product_data["name"]))
            existing = result.scalar_one_or_none()
            if not existing:
                product = Product(
                    category_id=category_id,
                    image_urls=[],
                    specs=[],
                    tags=product_data.pop("tags", []),
                    source="seed",
                    **product_data,
                )
                db.add(product)
                await db.flush()
                count += 1

        await db.commit()
        print(f"[OK] Created {count} products")

        # ── Summary ──
        cat_count = await db.scalar(select(func.count()).select_from(Category))
        prod_count = await db.scalar(select(func.count()).select_from(Product))
        print(f"\n[SUMMARY] Database contains {cat_count} categories and {prod_count} products")

    finally:
        await db.close()
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed_database())
