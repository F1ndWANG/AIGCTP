"""
Commerce Agent - 电商购物助手

Handles product recommendations, auto-shopping cart, and quick reorder.
"""
import json
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.services.llm import llm_service
from app.models.commerce import Product, Cart, CartItem, Order
from app.core.logging import get_logger

logger = get_logger(__name__)

COMMERCE_SYSTEM_PROMPT = """你是 AI 生活推荐系统的电商购物专家。你擅长根据用户需求推荐商品和帮助购物。

## 你的角色
- 你是一个专业、贴心的购物顾问
- 你会根据用户的描述推荐最合适的商品
- 你会考虑商品的价格、特性、适用场景
- 你会主动询问用户的具体需求，提供精准推荐

## 推荐原则
1. **需求匹配**: 根据用户描述的场景推荐最合适的商品
2. **性价比**: 考虑价格和品质的平衡
3. **多样性**: 推荐不同价位的选择
4. **实用性**: 推荐真正解决用户需求的产品
"""


async def commerce_recommend(
    user_message: str,
    user_id: int,
    db: AsyncSession,
) -> dict[str, Any]:
    """Search and recommend products based on user query.

    Returns:
        dict with keys: response (str), products (list[dict])
    """
    # Step 1: Use LLM to extract search intent
    extraction_prompt = f"""从用户的购物请求中提取搜索条件。

## 用户消息
{user_message}

## 输出格式
```json
{{
  "keywords": ["搜索关键词列表"],
  "category": "商品分类（如果没有则为空字符串）",
  "max_price": 最大价格（如果没有则为0）,
  "tags": ["相关标签列表"],
  "search_intent": "简短描述用户的购物需求"
}}
```
"""
    try:
        intent = await llm_service.extract_json(
            system_prompt="你是一个购物意图分析专家，从用户消息中提取搜索关键词。",
            messages=[{"role": "user", "content": extraction_prompt}],
        )
    except Exception as e:
        logger.warning("Commerce intent extraction failed: %s", e)
        intent = {"keywords": [user_message[:50]], "category": "", "max_price": 0, "tags": []}

    keywords = intent.get("keywords", [user_message[:50]])
    category_name = intent.get("category", "")
    max_price = intent.get("max_price", 0)
    tag_filter = intent.get("tags", [])

    # Step 2: Query products from DB
    query = select(Product).where(Product.status == "active")

    if keywords:
        from sqlalchemy import or_, String, cast
        like_conditions = [Product.name.ilike(f"%{kw}%") for kw in keywords]
        like_conditions.extend(cast(Product.tags, String).ilike(f"%{kw}%") for kw in keywords)
        query = query.where(or_(*like_conditions))

    if max_price and max_price > 0:
        query = query.where(Product.price <= max_price)

    if category_name:
        from app.models.commerce import Category
        cat_result = await db.execute(
            select(Category).where(Category.name.ilike(f"%{category_name}%"))
        )
        cat = cat_result.scalar_one_or_none()
        if cat:
            query = query.where(Product.category_id == cat.id)

    query = query.order_by(Product.rating.desc()).limit(20)
    result = await db.execute(query)
    products = list(result.scalars().all())

    # Step 3: Use LLM to rank and recommend
    if not products:
        # Broader search: just use first keyword
        if keywords:
            broad_query = select(Product).where(Product.status == "active")
            broad_query = broad_query.where(Product.name.ilike(f"%{keywords[0]}%"))
            broad_query = broad_query.limit(10)
            broad_result = await db.execute(broad_query)
            products = list(broad_result.scalars().all())

    if not products:
        # LLM fallback: use model knowledge to suggest products
        fallback_prompt = f"""用户想购买: 「{' '.join(keywords)}」
在我们的数据库中找不到匹配的商品。请根据你的知识给用户一些购买建议。

输出格式:
```json
{{
  "response": "给用户的完整回复，推荐具体的商品类型和购买建议，语气热情专业。说明虽然目前没有库存，但可以提供选购建议。",
  "suggested_keywords": ["替代搜索关键词1", "替代搜索关键词2", "替代搜索关键词3"]
}}
```"""
        try:
            fallback = await llm_service.extract_json(
                system_prompt=COMMERCE_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": fallback_prompt}],
            )
            resp = fallback.get("response", f"抱歉，暂时没有找到「{' '.join(keywords)}」相关的商品。")
            suggested = fallback.get("suggested_keywords", [])
            if suggested:
                resp += "\n\n💡 试试搜索: " + "、".join(suggested)
        except Exception:
            resp = f"抱歉，我没有找到符合「{' '.join(keywords)}」的商品。请试试其他关键词，或者告诉我您具体想买什么类型的商品？"
        return {"response": resp, "products": []}

    # Format products for LLM ranking
    products_str = json.dumps(
        [{
            "id": p.id,
            "name": p.name,
            "price": p.price,
            "unit": p.unit,
            "description": p.description[:100],
            "rating": p.rating,
            "tags": p.tags,
        } for p in products[:10]],
        ensure_ascii=False,
        indent=2,
    )

    ranking_prompt = f"""根据用户的购物需求，从以下商品中推荐最合适的 3-5 个。

## 用户需求
{intent.get('search_intent', user_message)}

## 可选商品
{products_str}

## 输出格式
```json
{{
  "recommended_ids": [推荐的商品ID列表，按适合程度排序],
  "response": "给用户的完整回复，热情专业，说明推荐理由，包含具体商品名称、价格和推荐原因",
  "cart_suggestion": "是否建议用户加入购物车（true/false）"
}}
```
"""
    try:
        ranking = await llm_service.extract_json(
            system_prompt=COMMERCE_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": ranking_prompt}],
        )
    except Exception as e:
        logger.warning("Commerce ranking failed: %s", e)
        ranking = {
            "recommended_ids": [p.id for p in products[:3]],
            "response": f"为您推荐以下商品: {', '.join(p.name for p in products[:3])}。如需了解更多信息，请告诉我！",
        }

    recommended_ids = ranking.get("recommended_ids", [p.id for p in products[:3]])
    recommended = [p for p in products if p.id in recommended_ids][:5]

    return {
        "response": ranking.get("response", f"为您推荐了 {len(recommended)} 件商品！"),
        "products": [{
            "id": p.id,
            "name": p.name,
            "price": p.price,
            "original_price": p.original_price,
            "description": p.description[:200],
            "image_urls": p.image_urls,
            "unit": p.unit,
            "rating": p.rating,
            "tags": p.tags,
            "stock": p.stock,
        } for p in recommended],
    }


async def auto_cart(
    user_message: str,
    user_id: int,
    context: dict,
    db: AsyncSession,
) -> dict[str, Any]:
    """Auto-generate shopping list and add items to cart.

    Returns:
        dict with keys: response (str), cart_items (list[dict])
    """
    extraction_prompt = f"""从用户的购物请求中提取要购买的商品信息。

## 用户消息
{user_message}

## 输出格式
```json
{{
  "items": [
    {{"product_name": "商品名称关键词", "quantity": 数量, "specs": {{"规格名": "规格值"}}}}
  ],
  "response": "给用户的确认回复，热情友好"
}}
```
"""
    try:
        parsed = await llm_service.extract_json(
            system_prompt="你是一个购物助手，从用户消息中提取要买的商品信息。",
            messages=[{"role": "user", "content": extraction_prompt}],
        )
    except Exception as e:
        logger.warning("Auto-cart extraction failed: %s", e)
        parsed = {
            "items": [{"product_name": user_message[:50], "quantity": 1, "specs": {}}],
            "response": "好的，已为您添加到购物车！",
        }

    wanted_items = parsed.get("items", [])
    response_text = parsed.get("response", "已为您处理购物请求！")
    added_items = []

    # Batch-fetch all wanted products
    product_name_map = {}
    if wanted_items:
        names = [w.get("product_name", "") for w in wanted_items if w.get("product_name")]
        if names:
            from sqlalchemy import or_
            name_conditions = [Product.name.ilike(f"%{n}%") for n in names]
            batch_result = await db.execute(
                select(Product).where(
                    Product.status == "active",
                    or_(*name_conditions),
                )
            )
            # Map each wanted name to the best matching product
            for p in batch_result.scalars().all():
                for w in wanted_items:
                    name_kw = w.get("product_name", "")
                    if name_kw and (name_kw.lower() in p.name.lower() or p.name.lower().startswith(name_kw.lower())):
                        product_name_map[name_kw] = p

    for wanted in wanted_items:
        name_kw = wanted.get("product_name", "")
        qty = wanted.get("quantity", 1)
        specs = wanted.get("specs", {})

        if not name_kw:
            continue

        # Find matching product (from batch-fetched map or fallback query)
        product = product_name_map.get(name_kw)
        if not product:
            result = await db.execute(
                select(Product).where(
                    Product.status == "active",
                    Product.name.ilike(f"%{name_kw}%"),
                ).limit(1)
            )
            product = result.scalar_one_or_none()
        if not product or product.stock < 1:
            continue

        # Get or create cart
        from sqlalchemy.orm import selectinload
        cart_result = await db.execute(
            select(Cart).where(Cart.user_id == user_id)
            .options(selectinload(Cart.items))
        )
        cart = cart_result.scalar_one_or_none()
        if not cart:
            cart = Cart(user_id=user_id)
            db.add(cart)
            await db.flush()
            cart.items = []

        # Check if same product+specs already in cart
        import json as _json
        spec_str = _json.dumps(specs, sort_keys=True, ensure_ascii=False)
        existing = None
        for ci in cart.items:
            if ci.product_id == product.id and _json.dumps(ci.specs or {}, sort_keys=True, ensure_ascii=False) == spec_str:
                existing = ci
                break

        if existing:
            existing.quantity += qty
        else:
            ci = CartItem(cart_id=cart.id, product_id=product.id, quantity=qty, specs=specs)
            db.add(ci)

        # Decrement stock
        product.stock = max(0, product.stock - qty)

        added_items.append({
            "product_id": product.id,
            "product_name": product.name,
            "quantity": qty,
            "price": product.price,
            "specs": specs,
        })

    await db.commit()

    if not added_items:
        return {
            "response": "抱歉，我没有找到匹配的商品或库存不足。请告诉我更具体的商品名称？",
            "cart_items": [],
        }

    return {
        "response": response_text,
        "cart_items": added_items,
    }


async def quick_reorder(
    user_id: int,
    db: AsyncSession,
) -> dict[str, Any]:
    """One-click reorder: add all items from most recent completed order to cart.

    Returns:
        dict with keys: response (str), order_id (int), items_added (int)
    """
    result = await db.execute(
        select(Order)
        .where(Order.user_id == user_id, Order.status.in_(["completed", "paid", "shipped"]))
        .order_by(Order.created_at.desc())
        .limit(1)
    )
    order = result.scalar_one_or_none()

    if not order:
        return {"response": "您还没有历史订单，无法复购。去看看有什么想买的吧！", "order_id": 0, "items_added": 0}

    from sqlalchemy.orm import selectinload
    import json as _json

    cart_result = await db.execute(
        select(Cart).where(Cart.user_id == user_id)
        .options(selectinload(Cart.items))
    )
    cart = cart_result.scalar_one_or_none()
    if not cart:
        cart = Cart(user_id=user_id)
        db.add(cart)
        await db.flush()
        cart.items = []

    order_items = order.items or []
    added_count = 0

    # Batch-fetch all products
    order_pids = [oi.get("product_id") for oi in order_items if oi.get("product_id")]
    order_products_map = {}
    if order_pids:
        op_result = await db.execute(
            select(Product).where(Product.id.in_(set(order_pids)))
        )
        order_products_map = {p.id: p for p in op_result.scalars().all()}

    for oi in order_items:
        pid = oi.get("product_id")
        product = order_products_map.get(pid)
        if not product or product.status != "active" or product.stock < 1:
            continue

        qty = min(oi.get("quantity", 1), product.stock)
        specs = oi.get("specs", {})

        spec_str = _json.dumps(specs, sort_keys=True, ensure_ascii=False)
        existing = None
        for ci in cart.items:
            if ci.product_id == pid and _json.dumps(ci.specs or {}, sort_keys=True, ensure_ascii=False) == spec_str:
                existing = ci
                break

        if existing:
            existing.quantity += qty
        else:
            ci = CartItem(cart_id=cart.id, product_id=pid, quantity=qty, specs=specs)
            db.add(ci)

        product.stock = max(0, product.stock - qty)
        added_count += 1

    await db.commit()

    return {
        "response": f"已为您将订单 #{order.id} 中的 {added_count} 件商品重新加入购物车！",
        "order_id": order.id,
        "items_added": added_count,
    }
