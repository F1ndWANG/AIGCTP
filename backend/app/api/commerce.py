import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.commerce import Category, Product, Cart, CartItem, Order
from app.schemas.commerce import (
    CategoryResponse, CategoryCreateRequest,
    ProductRequest, ProductResponse, ProductListItem,
    CartResponse, CartItemResponse, AddCartItemRequest, UpdateCartItemRequest,
    OrderResponse, OrderListItem, OrderItemResponse, CreateOrderRequest,
)

from pydantic import BaseModel


class OrderStatusUpdate(BaseModel):
    status: str


VALID_ORDER_TRANSITIONS = {
    "pending": ["paid", "cancelled"],
    "paid": ["shipped", "cancelled"],
    "shipped": ["completed"],
    "completed": [],
    "cancelled": [],
}

router = APIRouter(prefix="/commerce", tags=["commerce"])


# ==================== Categories ====================


@router.get("/categories", response_model=list[CategoryResponse])
async def list_categories(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Category).order_by(Category.sort_order.asc()))
    categories = result.scalars().all()
    return [CategoryResponse.model_validate(c) for c in categories if c is not None]


@router.post("/categories", response_model=CategoryResponse, status_code=201)
async def create_category(
    payload: CategoryCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    cat = Category(**payload.model_dump())
    db.add(cat)
    await db.commit()
    await db.refresh(cat)
    return CategoryResponse.model_validate(cat)


# ==================== Products ====================


@router.get("/products")
async def list_products(
    category_id: Optional[int] = Query(None),
    keyword: Optional[str] = Query(None),
    min_price: Optional[float] = Query(None),
    max_price: Optional[float] = Query(None),
    tags: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(Product).where(Product.status == "active")

    if category_id is not None:
        query = query.where(Product.category_id == category_id)
    if keyword:
        like = f"%{keyword}%"
        query = query.where(
            or_(Product.name.ilike(like), Product.tags.ilike(like))
        )
    if min_price is not None:
        query = query.where(Product.price >= min_price)
    if max_price is not None:
        query = query.where(Product.price <= max_price)
    if tags:
        tag_list = [t.strip() for t in tags.split(",") if t.strip()]
        for tag in tag_list:
            query = query.where(Product.tags.as_string().ilike(f"%{tag}%"))

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


@router.get("/products/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return ProductResponse.model_validate(product)


@router.post("/products", response_model=ProductResponse, status_code=201)
async def create_product(
    payload: ProductRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    product = Product(**payload.model_dump())
    db.add(product)
    await db.commit()
    await db.refresh(product)
    return ProductResponse.model_validate(product)


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
        price = item.product.price if item.product else 0
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


@router.get("/cart", response_model=CartResponse)
async def get_cart(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    cart = await _get_or_create_cart(current_user.id, db)
    return _build_cart_response(cart)


@router.post("/cart/items", response_model=CartItemResponse, status_code=201)
async def add_cart_item(
    payload: AddCartItemRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    product = await db.get(Product, payload.product_id)
    if not product or product.status != "active":
        raise HTTPException(status_code=404, detail="Product not found or not available")
    if product.stock < 1:
        raise HTTPException(status_code=400, detail="Product out of stock")

    cart = await _get_or_create_cart(current_user.id, db)

    spec_json = json.dumps(payload.specs, sort_keys=True, ensure_ascii=False)
    existing_item = None
    for item in cart.items:
        if item.product_id == payload.product_id and json.dumps(item.specs or {}, sort_keys=True, ensure_ascii=False) == spec_json:
            existing_item = item
            break

    if existing_item:
        existing_item.quantity += payload.quantity
        await db.commit()
        await db.refresh(existing_item)
        item = existing_item
    else:
        item = CartItem(
            cart_id=cart.id,
            product_id=payload.product_id,
            quantity=payload.quantity,
            specs=payload.specs,
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
        price=product.price,
        unit=product.unit,
        quantity=item.quantity,
        specs=item.specs or {},
        created_at=item.created_at,
    )


@router.put("/cart/items/{item_id}", response_model=CartItemResponse)
async def update_cart_item(
    item_id: int,
    payload: UpdateCartItemRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
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
        price=product.price if product else 0,
        unit=product.unit if product else "",
        quantity=item.quantity,
        specs=item.specs or {},
        created_at=item.created_at,
    )


@router.delete("/cart/items/{item_id}", status_code=204)
async def remove_cart_item(
    item_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(CartItem)
        .join(Cart)
        .where(CartItem.id == item_id, Cart.user_id == current_user.id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Cart item not found")
    await db.delete(item)
    await db.commit()


@router.delete("/cart", status_code=204)
async def clear_cart(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Cart)
        .where(Cart.user_id == current_user.id)
        .options(selectinload(Cart.items))
    )
    cart = result.scalar_one_or_none()
    if cart:
        for item in list(cart.items):
            await db.delete(item)
        await db.commit()


# ==================== Orders ====================


@router.post("/orders", response_model=OrderResponse, status_code=201)
async def create_order(
    payload: CreateOrderRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
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
            "price": product.price,
            "quantity": item.quantity,
            "specs": item.specs or {},
            "image_url": product.image_urls[0] if product.image_urls else "",
        })
        total += product.price * item.quantity

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
    return _build_order_response(order)


@router.get("/orders", response_model=list[OrderListItem])
async def list_orders(
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
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


@router.get("/orders/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
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
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
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
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
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


@router.post("/orders/{order_id}/cancel", response_model=OrderResponse)
async def cancel_order(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
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
