import json
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import String, cast, select, func, or_
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.attributes import flag_modified

from app.api.deps import CurrentUser, DbSession
from app.models.commerce import Category, Product, Cart, CartItem, Order
from app.services.product_images import generate_product_image, has_generated_product_image
from app.services.recommendation import recommendation_service
from app.schemas.commerce import (
    CategoryResponse, CategoryCreateRequest,
    ProductRequest, ProductResponse, ProductListItem,
    CartResponse, CartItemResponse, AddCartItemRequest, AddRecommendedCartItemRequest, UpdateCartItemRequest,
    OrderResponse, OrderListItem, OrderItemResponse, CreateOrderRequest,
)

from pydantic import BaseModel


class OrderStatusUpdate(BaseModel):
    status: str


class ProductImageGenerateRequest(BaseModel):
    product_ids: list[int]


VALID_ORDER_TRANSITIONS = {
    "pending": ["paid", "cancelled"],
    "paid": ["shipped", "cancelled"],
    "shipped": ["completed"],
    "completed": [],
    "cancelled": [],
}

router = APIRouter(prefix="/commerce", tags=["commerce"])


# ==================== Categories ====================


@router.get("/categories", summary="List categories", response_model=list[CategoryResponse])
async def list_categories(
    current_user: CurrentUser,
    db: DbSession,
):
    result = await db.execute(select(Category).order_by(Category.sort_order.asc()))
    categories = result.scalars().all()
    return [CategoryResponse.model_validate(c) for c in categories if c is not None]


@router.post("/categories", summary="Create category", response_model=CategoryResponse, status_code=201)
async def create_category(
    payload: CategoryCreateRequest,
    current_user: CurrentUser,
    db: DbSession,
):
    cat = Category(**payload.model_dump())
    db.add(cat)
    await db.commit()
    await db.refresh(cat)
    return CategoryResponse.model_validate(cat)


# ==================== Products ====================


@router.get("/products", summary="List products")
async def list_products(
    current_user: CurrentUser,
    db: DbSession,
    category_id: Optional[int] = Query(None),
    keyword: Optional[str] = Query(None),
    min_price: Optional[float] = Query(None),
    max_price: Optional[float] = Query(None),
    tags: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    query = select(Product).where(Product.status == "active")

    if category_id is not None:
        query = query.where(Product.category_id == category_id)
    if keyword:
        like = f"%{keyword}%"
        query = query.where(
            or_(Product.name.ilike(like), cast(Product.tags, String).ilike(like))
        )
    if min_price is not None:
        query = query.where(Product.price >= min_price)
    if max_price is not None:
        query = query.where(Product.price <= max_price)
    if tags:
        tag_list = [t.strip() for t in tags.split(",") if t.strip()]
        for tag in tag_list:
            query = query.where(cast(Product.tags, String).ilike(f"%{tag}%"))

    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)

    query = query.order_by(Product.rating.desc(), Product.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    products = result.scalars().all()

    return {
        "items": [ProductListItem.model_validate(p) for p in products],
        "total": total or 0,
    }


@router.get("/products/{product_id}", summary="Get product detail", response_model=ProductResponse)
async def get_product(
    product_id: int,
    current_user: CurrentUser,
    db: DbSession,
):
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return ProductResponse.model_validate(product)


@router.post("/products", summary="Create product", response_model=ProductResponse, status_code=201)
async def create_product(
    payload: ProductRequest,
    current_user: CurrentUser,
    db: DbSession,
):
    product = Product(**payload.model_dump())
    db.add(product)
    await db.commit()
    await db.refresh(product)
    return ProductResponse.model_validate(product)


@router.post("/products/{product_id}/image", summary="Generate product image")
async def generate_single_product_image(
    product_id: int,
    current_user: CurrentUser,
    db: DbSession,
):
    product = await db.get(Product, product_id)
    if not product or product.status != "active":
        raise HTTPException(status_code=404, detail="Product not found")

    if has_generated_product_image(product):
        return {"product_id": product.id, "image_url": product.image_urls[0], "generated": False}

    try:
        image_url = await generate_product_image(product)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    existing = [url for url in (product.image_urls or []) if url != image_url]
    product.image_urls = [image_url, *existing]
    flag_modified(product, "image_urls")
    await db.commit()
    return {"product_id": product.id, "image_url": image_url, "generated": True}


@router.post("/products/images/generate", summary="Generate missing product images")
async def generate_missing_product_images(
    payload: ProductImageGenerateRequest,
    current_user: CurrentUser,
    db: DbSession,
):
    if not payload.product_ids:
        return {"items": []}

    result = await db.execute(
        select(Product).where(Product.id.in_(set(payload.product_ids)), Product.status == "active")
    )
    products = list(result.scalars().all())
    items = []
    for product in products:
        if has_generated_product_image(product):
            items.append({"product_id": product.id, "image_url": product.image_urls[0], "generated": False})
            continue
        try:
            image_url = await generate_product_image(product)
        except RuntimeError as exc:
            items.append({"product_id": product.id, "error": str(exc), "generated": False})
            continue
        existing = [url for url in (product.image_urls or []) if url != image_url]
        product.image_urls = [image_url, *existing]
        flag_modified(product, "image_urls")
        items.append({"product_id": product.id, "image_url": image_url, "generated": True})

    await db.commit()
    return {"items": items}


# ==================== Cart ====================


async def _get_or_create_cart(user_id: int, db: AsyncSession) -> Cart:
    result = await db.execute(
        select(Cart)
        .where(Cart.user_id == user_id)
        .options(selectinload(Cart.items).selectinload(CartItem.product))
    )
    cart = result.scalar_one_or_none()
    if not cart:
        cart = Cart(user_id=user_id)
        db.add(cart)
        await db.commit()
        await db.refresh(cart)
        cart.items = []
    return cart


def _build_cart_response(cart: Cart) -> CartResponse:
    items = []
    total = 0.0
    for item in cart.items:
        price = float(item.product.price) if item.product and item.product.price is not None else 0.0
        total += price * item.quantity
        items.append(CartItemResponse(
            id=item.id,
            product_id=item.product_id,
            product_name=item.product.name if item.product else "",
            product_image=(item.product.image_urls[0] if item.product and item.product.image_urls else ""),
            price=price,
            unit=item.product.unit if item.product else "",
            quantity=item.quantity,
            specs=item.specs or {},
            created_at=item.created_at,
        ))
    return CartResponse(
        id=cart.id,
        items=items,
        total_amount=round(total, 2),
        created_at=cart.created_at,
        updated_at=cart.updated_at,
    )


async def _add_product_to_cart(
    product: Product,
    quantity: int,
    specs: dict,
    user_id: int,
    db: AsyncSession,
) -> CartItemResponse:
    if product.status != "active":
        raise HTTPException(status_code=404, detail="Product not found or not available")
    if product.stock < 1:
        raise HTTPException(status_code=400, detail="Product out of stock")

    cart = await _get_or_create_cart(user_id, db)
    spec_json = json.dumps(specs, sort_keys=True, ensure_ascii=False)
    existing_item = None
    for item in cart.items:
        if item.product_id == product.id and json.dumps(item.specs or {}, sort_keys=True, ensure_ascii=False) == spec_json:
            existing_item = item
            break

    if existing_item:
        existing_item.quantity += quantity
        await db.commit()
        await db.refresh(existing_item)
        item = existing_item
    else:
        item = CartItem(
            cart_id=cart.id,
            product_id=product.id,
            quantity=quantity,
            specs=specs,
        )
        db.add(item)
        await db.commit()
        await db.refresh(item)

    await db.refresh(product)
    return CartItemResponse(
        id=item.id,
        product_id=item.product_id,
        product_name=product.name,
        product_image=product.image_urls[0] if product.image_urls else "",
        price=float(product.price),
        unit=product.unit,
        quantity=item.quantity,
        specs=item.specs or {},
        created_at=item.created_at,
    )


async def _get_or_create_ai_category(db: AsyncSession) -> Category:
    result = await db.execute(select(Category).where(Category.name == "AI 推荐"))
    category = result.scalar_one_or_none()
    if category:
        return category
    category = Category(name="AI 推荐", description="由 AI 对话生成的个性化商品", icon="✨", sort_order=99)
    db.add(category)
    await db.flush()
    return category


async def _resolve_recommended_product(payload: AddRecommendedCartItemRequest, db: AsyncSession) -> Product:
    if payload.product_id:
        product = await db.get(Product, payload.product_id)
        if product and product.status == "active" and product.stock > 0:
            return product

    name = (payload.product_name or "").strip() or "行程推荐好物"
    result = await db.execute(select(Product).where(Product.name == name, Product.status == "active"))
    product = result.scalar_one_or_none()
    if product:
        return product

    category = await _get_or_create_ai_category(db)
    price = payload.price if payload.price and payload.price > 0 else 79.0
    product = Product(
        name=name,
        description=payload.reason or "来自行程推荐的好物",
        price=price,
        category_id=category.id,
        image_urls=[],
        stock=99,
        unit="件",
        specs=[],
        tags=["AI推荐", "行程推荐"],
        rating=4.5,
        status="active",
        source="ai_generated",
    )
    db.add(product)
    await db.flush()
    return product


@router.get("/cart", summary="Get cart", response_model=CartResponse)
async def get_cart(
    current_user: CurrentUser,
    db: DbSession,
):
    cart = await _get_or_create_cart(current_user.id, db)
    return _build_cart_response(cart)


@router.post("/cart/items", summary="Add item to cart", response_model=CartItemResponse, status_code=201)
async def add_cart_item(
    payload: AddCartItemRequest,
    current_user: CurrentUser,
    db: DbSession,
):
    product = await db.get(Product, payload.product_id)
    if not product or product.status != "active":
        raise HTTPException(status_code=404, detail="Product not found or not available")
    item = await _add_product_to_cart(product, payload.quantity, payload.specs, current_user.id, db)
    await recommendation_service.track(
        db,
        user_id=current_user.id,
        domain="commerce",
        item_type="product",
        item_id=product.id,
        event_type="add_cart",
        context={"quantity": payload.quantity, "specs": payload.specs, "product_name": product.name},
    )
    return item


@router.post("/cart/recommended-item", summary="Add recommended item to cart", response_model=CartItemResponse, status_code=201)
async def add_recommended_cart_item(
    payload: AddRecommendedCartItemRequest,
    current_user: CurrentUser,
    db: DbSession,
):
    product = await _resolve_recommended_product(payload, db)
    item = await _add_product_to_cart(product, payload.quantity, payload.specs, current_user.id, db)
    await recommendation_service.track(
        db,
        user_id=current_user.id,
        domain="commerce",
        item_type="product",
        item_id=product.id,
        event_type="add_cart",
        context={"quantity": payload.quantity, "source": "recommended_item", "product_name": product.name},
    )
    return item


@router.put("/cart/items/{item_id}", summary="Update cart item", response_model=CartItemResponse)
async def update_cart_item(
    item_id: int,
    payload: UpdateCartItemRequest,
    current_user: CurrentUser,
    db: DbSession,
):
    cart = await _get_or_create_cart(current_user.id, db)
    item = next((i for i in cart.items if i.id == item_id), None)
    if not item:
        raise HTTPException(status_code=404, detail="Cart item not found")

    if payload.quantity < 1:
        raise HTTPException(status_code=400, detail="Quantity must be at least 1")

    item.quantity = payload.quantity
    await db.commit()

    product = item.product
    return CartItemResponse(
        id=item.id,
        product_id=item.product_id,
        product_name=product.name if product else "",
        product_image=product.image_urls[0] if product and product.image_urls else "",
        price=float(product.price) if product and product.price is not None else 0,
        unit=product.unit if product else "",
        quantity=item.quantity,
        specs=item.specs or {},
        created_at=item.created_at,
    )


@router.delete("/cart/items/{item_id}", summary="Remove cart item", status_code=204)
async def remove_cart_item(
    item_id: int,
    current_user: CurrentUser,
    db: DbSession,
):
    result = await db.execute(
        select(CartItem)
        .join(Cart)
        .where(CartItem.id == item_id, Cart.user_id == current_user.id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Cart item not found")

    # Restore product stock
    product = await db.get(Product, item.product_id)
    if product:
        product.stock += item.quantity
        flag_modified(product, "stock")

    await db.delete(item)
    await db.commit()


@router.delete("/cart", status_code=204)
async def clear_cart(
    current_user: CurrentUser,
    db: DbSession,
):
    result = await db.execute(
        select(Cart)
        .where(Cart.user_id == current_user.id)
        .options(selectinload(Cart.items))
    )
    cart = result.scalar_one_or_none()
    if cart:
        for item in list(cart.items):
            # Restore product stock
            product = await db.get(Product, item.product_id)
            if product:
                product.stock += item.quantity
            await db.delete(item)
        await db.commit()


# ==================== Orders ====================


@router.post("/orders", response_model=OrderResponse, status_code=201)
async def create_order(
    payload: CreateOrderRequest,
    current_user: CurrentUser,
    db: DbSession,
):
    cart = await _get_or_create_cart(current_user.id, db)
    if not cart.items:
        raise HTTPException(status_code=400, detail="Cart is empty")

    order_items = []
    total = 0.0
    for item in cart.items:
        product = item.product
        if not product or product.status != "active":
            raise HTTPException(status_code=400, detail=f"Product '{product.name if product else 'N/A'}' is not available")
        if product.stock < item.quantity:
            raise HTTPException(status_code=400, detail=f"Product '{product.name}' has insufficient stock (available: {product.stock})")
        order_items.append({
            "product_id": product.id,
            "name": product.name,
            "price": float(product.price),
            "quantity": item.quantity,
            "specs": item.specs or {},
            "image_url": product.image_urls[0] if product.image_urls else "",
        })
        total += float(product.price) * item.quantity

    order = Order(
        user_id=current_user.id,
        status="pending",
        total_amount=round(total, 2),
        items=order_items,
        shipping_address=payload.shipping_address,
        contact_phone=payload.contact_phone,
        notes=payload.notes,
    )
    db.add(order)

    for item in cart.items:
        product = item.product
        if product:
            product.stock -= item.quantity
        await db.delete(item)

    await db.commit()
    await db.refresh(order)
    for order_item in order_items:
        await recommendation_service.track(
            db,
            user_id=current_user.id,
            domain="commerce",
            item_type="product",
            item_id=order_item.get("product_id"),
            event_type="order",
            context={"order_id": order.id, "item": order_item},
            commit=False,
        )
    await db.commit()
    return _build_order_response(order)


@router.get("/orders", summary="List orders", response_model=list[OrderListItem])
async def list_orders(
    current_user: CurrentUser,
    db: DbSession,
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    query = select(Order).where(Order.user_id == current_user.id)
    if status:
        query = query.where(Order.status == status)
    query = query.order_by(Order.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    orders = result.scalars().all()

    items = []
    for order in orders:
        order_items = order.items or []
        items.append(OrderListItem(
            id=order.id,
            status=order.status,
            total_amount=order.total_amount,
            item_count=len(order_items),
            first_item_name=order_items[0]["name"] if order_items else "",
            created_at=order.created_at,
        ))
    return items


@router.get("/orders/{order_id}", summary="Get order detail", response_model=OrderResponse)
async def get_order(
    order_id: int,
    current_user: CurrentUser,
    db: DbSession,
):
    result = await db.execute(
        select(Order).where(Order.id == order_id, Order.user_id == current_user.id)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return _build_order_response(order)


@router.post("/orders/{order_id}/reorder", response_model=CartResponse)
async def reorder(
    order_id: int,
    current_user: CurrentUser,
    db: DbSession,
):
    result = await db.execute(
        select(Order).where(Order.id == order_id, Order.user_id == current_user.id)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    cart = await _get_or_create_cart(current_user.id, db)
    order_items = order.items or []

    # Batch-fetch all products
    pids = [oi.get("product_id") for oi in order_items if oi.get("product_id")]
    products_map = {}
    if pids:
        prod_result = await db.execute(
            select(Product).where(Product.id.in_(set(pids)))
        )
        products_map = {p.id: p for p in prod_result.scalars().all()}

    for oi in order_items:
        pid = oi.get("product_id")
        product = products_map.get(pid)
        if not product or product.status != "active":
            continue

        spec_json = json.dumps(oi.get("specs", {}), sort_keys=True, ensure_ascii=False)
        existing = None
        for ci in cart.items:
            if ci.product_id == pid and json.dumps(ci.specs or {}, sort_keys=True, ensure_ascii=False) == spec_json:
                existing = ci
                break

        if existing:
            existing.quantity += oi.get("quantity", 1)
        else:
            ci = CartItem(
                cart_id=cart.id,
                product_id=pid,
                quantity=oi.get("quantity", 1),
                specs=oi.get("specs", {}),
            )
            db.add(ci)
            cart.items.append(ci)

    await db.commit()
    await db.refresh(cart)
    return _build_cart_response(cart)


@router.patch("/orders/{order_id}/status", response_model=OrderResponse)
async def update_order_status(
    order_id: int,
    payload: OrderStatusUpdate,
    current_user: CurrentUser,
    db: DbSession,
):
    result = await db.execute(
        select(Order).where(Order.id == order_id, Order.user_id == current_user.id)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    allowed = VALID_ORDER_TRANSITIONS.get(order.status, [])
    if payload.status not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot transition from '{order.status}' to '{payload.status}'",
        )

    order.status = payload.status
    await db.commit()
    await db.refresh(order)
    return _build_order_response(order)


@router.post("/orders/{order_id}/cancel", summary="Cancel order", response_model=OrderResponse)
async def cancel_order(
    order_id: int,
    current_user: CurrentUser,
    db: DbSession,
):
    result = await db.execute(
        select(Order).where(Order.id == order_id, Order.user_id == current_user.id)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.status not in ("pending", "paid"):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel an order with status '{order.status}'",
        )

    # Restore stock
    order_items = order.items or []
    pids = [oi.get("product_id") for oi in order_items if oi.get("product_id")]
    if pids:
        prod_result = await db.execute(
            select(Product).where(Product.id.in_(set(pids)))
        )
        for product in prod_result.scalars().all():
            for oi in order_items:
                if oi.get("product_id") == product.id:
                    product.stock += oi.get("quantity", 1)

    order.status = "cancelled"
    await db.commit()
    await db.refresh(order)
    return _build_order_response(order)


def _build_order_response(order: Order) -> OrderResponse:
    items_data = order.items or []
    return OrderResponse(
        id=order.id,
        status=order.status,
        total_amount=order.total_amount,
        items=[OrderItemResponse(**i) for i in items_data],
        shipping_address=order.shipping_address,
        contact_phone=order.contact_phone,
        notes=order.notes,
        created_at=order.created_at,
        updated_at=order.updated_at,
    )
