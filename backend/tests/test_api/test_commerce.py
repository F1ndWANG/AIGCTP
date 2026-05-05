"""Tests for commerce API: categories, products, cart, and orders."""
import pytest


@pytest.fixture
async def seed_category(session):
    """Seed a test category and return it."""
    from app.models.commerce import Category
    cat = Category(name="测试分类", description="测试描述", icon="test", sort_order=1)
    session.add(cat)
    await session.commit()
    await session.refresh(cat)
    return cat


@pytest.fixture
async def seed_product(seed_category, session):
    """Seed a test product and return it."""
    from app.models.commerce import Product
    product = Product(
        name="测试商品",
        description="这是一个测试商品",
        price=99.9,
        stock=100,
        unit="件",
        category_id=seed_category.id,
        tags=["测试", "sample"],
        rating=4.5,
        status="active",
    )
    session.add(product)
    await session.commit()
    await session.refresh(product)
    return product


class TestCategories:
    async def test_list_categories_empty(self, client, auth_headers):
        resp = await client.get("/api/v1/commerce/categories", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_create_and_list_categories(self, client, auth_headers, session):
        from app.models.commerce import Category
        cat = Category(name="食品饮料", description="食品分类", sort_order=1)
        session.add(cat)
        await session.commit()

        resp = await client.get("/api/v1/commerce/categories", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        assert data[0]["name"] == "食品饮料"

    async def test_create_category(self, client, auth_headers):
        resp = await client.post("/api/v1/commerce/categories", headers=auth_headers, json={
            "name": "新分类",
            "description": "新分类描述",
            "sort_order": 2,
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "新分类"
        assert data["description"] == "新分类描述"
        assert "id" in data

    async def test_create_category_unauthorized(self, client):
        resp = await client.post("/api/v1/commerce/categories", json={
            "name": "新分类",
        })
        assert resp.status_code == 401


class TestProducts:
    async def test_list_products_empty(self, client, auth_headers):
        resp = await client.get("/api/v1/commerce/products", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["items"] == []

    async def test_list_products_with_data(self, client, auth_headers, session):
        from app.models.commerce import Category, Product
        cat = Category(name="数码", description="数码分类", sort_order=1)
        session.add(cat)
        await session.flush()
        p1 = Product(name="测试手机", price=2999, stock=50, category_id=cat.id,
                      tags=["数码", "手机"], rating=4.8, status="active")
        p2 = Product(name="测试耳机", price=199, stock=100, category_id=cat.id,
                      tags=["数码", "音频"], rating=4.5, status="active")
        session.add_all([p1, p2])
        await session.commit()

        resp = await client.get("/api/v1/commerce/products", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2

    async def test_list_products_filter_by_keyword(self, client, auth_headers, session):
        from app.models.commerce import Category, Product
        cat = Category(name="数码", description="数码分类", sort_order=1)
        session.add(cat)
        await session.flush()
        p1 = Product(name="智能手机", price=2999, stock=50, category_id=cat.id,
                      tags=["手机"], rating=4.8, status="active")
        p2 = Product(name="无线耳机", price=199, stock=100, category_id=cat.id,
                      tags=["耳机"], rating=4.5, status="active")
        session.add_all([p1, p2])
        await session.commit()

        resp = await client.get("/api/v1/commerce/products?keyword=手机", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["name"] == "智能手机"

    async def test_list_products_filter_by_price(self, client, auth_headers, session):
        from app.models.commerce import Category, Product
        cat = Category(name="数码", description="数码分类", sort_order=1)
        session.add(cat)
        await session.flush()
        p1 = Product(name="高端手机", price=5999, stock=50, category_id=cat.id,
                      tags=["手机"], rating=4.9, status="active")
        p2 = Product(name="平价耳机", price=99, stock=100, category_id=cat.id,
                      tags=["耳机"], rating=4.0, status="active")
        session.add_all([p1, p2])
        await session.commit()

        resp = await client.get("/api/v1/commerce/products?max_price=500", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["name"] == "平价耳机"

    async def test_get_product_by_id(self, client, auth_headers, seed_product):
        resp = await client.get(f"/api/v1/commerce/products/{seed_product.id}", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "测试商品"
        assert data["price"] == 99.9
        assert data["stock"] == 100

    async def test_get_product_not_found(self, client, auth_headers):
        resp = await client.get("/api/v1/commerce/products/99999", headers=auth_headers)
        assert resp.status_code == 404

    async def test_create_product(self, client, auth_headers, seed_category):
        resp = await client.post("/api/v1/commerce/products", headers=auth_headers, json={
            "name": "新商品",
            "price": 199.0,
            "stock": 50,
            "unit": "个",
            "category_id": seed_category.id,
            "tags": ["新品"],
            "status": "active",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "新商品"
        assert data["price"] == 199.0
        assert "id" in data

    async def test_create_product_unauthorized(self, client):
        resp = await client.post("/api/v1/commerce/products", json={
            "name": "新商品", "price": 100, "stock": 10,
        })
        assert resp.status_code == 401


class TestCart:
    async def test_get_empty_cart(self, client, auth_headers):
        resp = await client.get("/api/v1/commerce/cart", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["total_amount"] == 0.0

    async def test_add_item_to_cart(self, client, auth_headers, seed_product):
        resp = await client.post("/api/v1/commerce/cart/items", headers=auth_headers, json={
            "product_id": seed_product.id,
            "quantity": 2,
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["product_id"] == seed_product.id
        assert data["quantity"] == 2
        assert data["product_name"] == "测试商品"

    async def test_add_item_increases_quantity(self, client, auth_headers, seed_product):
        # First add
        await client.post("/api/v1/commerce/cart/items", headers=auth_headers, json={
            "product_id": seed_product.id, "quantity": 1,
        })
        # Second add — same product, same specs → quantity should increase
        resp = await client.post("/api/v1/commerce/cart/items", headers=auth_headers, json={
            "product_id": seed_product.id, "quantity": 3,
        })
        assert resp.status_code == 201
        assert resp.json()["quantity"] == 4  # 1 + 3

    async def test_add_item_out_of_stock(self, client, auth_headers, session):
        from app.models.commerce import Category, Product
        cat = Category(name="测试", description="", sort_order=1)
        session.add(cat)
        await session.flush()
        product = Product(name="缺货商品", price=50, stock=0, category_id=cat.id, status="active")
        session.add(product)
        await session.commit()
        await session.refresh(product)

        resp = await client.post("/api/v1/commerce/cart/items", headers=auth_headers, json={
            "product_id": product.id, "quantity": 1,
        })
        assert resp.status_code == 400
        assert "stock" in resp.json()["detail"].lower()

    async def test_add_item_inactive_product(self, client, auth_headers, session):
        from app.models.commerce import Category, Product
        cat = Category(name="测试", description="", sort_order=1)
        session.add(cat)
        await session.flush()
        product = Product(name="下架商品", price=50, stock=10, category_id=cat.id,
                          status="inactive")
        session.add(product)
        await session.commit()
        await session.refresh(product)

        resp = await client.post("/api/v1/commerce/cart/items", headers=auth_headers, json={
            "product_id": product.id, "quantity": 1,
        })
        assert resp.status_code == 404

    async def test_add_item_product_not_found(self, client, auth_headers):
        resp = await client.post("/api/v1/commerce/cart/items", headers=auth_headers, json={
            "product_id": 99999, "quantity": 1,
        })
        assert resp.status_code == 404

    async def test_update_cart_item_quantity(self, client, auth_headers, seed_product):
        add = await client.post("/api/v1/commerce/cart/items", headers=auth_headers, json={
            "product_id": seed_product.id, "quantity": 1,
        })
        item_id = add.json()["id"]

        resp = await client.put(f"/api/v1/commerce/cart/items/{item_id}", headers=auth_headers, json={
            "quantity": 5,
        })
        assert resp.status_code == 200
        assert resp.json()["quantity"] == 5

    async def test_update_cart_item_invalid_quantity(self, client, auth_headers, seed_product):
        add = await client.post("/api/v1/commerce/cart/items", headers=auth_headers, json={
            "product_id": seed_product.id, "quantity": 1,
        })
        item_id = add.json()["id"]

        resp = await client.put(f"/api/v1/commerce/cart/items/{item_id}", headers=auth_headers, json={
            "quantity": 0,
        })
        assert resp.status_code == 400

    async def test_update_cart_item_not_found(self, client, auth_headers):
        resp = await client.put("/api/v1/commerce/cart/items/99999", headers=auth_headers, json={
            "quantity": 2,
        })
        assert resp.status_code == 404

    async def test_remove_cart_item(self, client, auth_headers, seed_product, session):
        add = await client.post("/api/v1/commerce/cart/items", headers=auth_headers, json={
            "product_id": seed_product.id, "quantity": 1,
        })
        item_id = add.json()["id"]

        resp = await client.delete(f"/api/v1/commerce/cart/items/{item_id}", headers=auth_headers)
        assert resp.status_code == 204

        session.expire_all()
        # Verify cart is empty
        cart = await client.get("/api/v1/commerce/cart", headers=auth_headers)
        assert cart.json()["items"] == []

    async def test_remove_cart_item_not_found(self, client, auth_headers):
        resp = await client.delete("/api/v1/commerce/cart/items/99999", headers=auth_headers)
        assert resp.status_code == 404

    async def test_clear_cart(self, client, auth_headers, seed_product, session):
        # Add item to cart
        await client.post("/api/v1/commerce/cart/items", headers=auth_headers, json={
            "product_id": seed_product.id, "quantity": 2,
        })

        resp = await client.delete("/api/v1/commerce/cart", headers=auth_headers)
        assert resp.status_code == 204

        session.expire_all()
        cart = await client.get("/api/v1/commerce/cart", headers=auth_headers)
        assert cart.json()["items"] == []


class TestOrders:
    async def test_create_order_from_cart(self, client, auth_headers, seed_product):
        # Add to cart first
        await client.post("/api/v1/commerce/cart/items", headers=auth_headers, json={
            "product_id": seed_product.id, "quantity": 2,
        })

        resp = await client.post("/api/v1/commerce/orders", headers=auth_headers, json={
            "shipping_address": "测试地址",
            "contact_phone": "13800138000",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "pending"
        assert data["total_amount"] == 99.9 * 2
        assert len(data["items"]) == 1
        assert data["items"][0]["name"] == "测试商品"
        assert data["shipping_address"] == "测试地址"

    async def test_create_order_empty_cart(self, client, auth_headers):
        resp = await client.post("/api/v1/commerce/orders", headers=auth_headers, json={})
        assert resp.status_code == 400
        assert "empty" in resp.json()["detail"].lower()

    async def test_list_orders(self, client, auth_headers, seed_product):
        # Create an order
        await client.post("/api/v1/commerce/cart/items", headers=auth_headers, json={
            "product_id": seed_product.id, "quantity": 1,
        })
        await client.post("/api/v1/commerce/orders", headers=auth_headers, json={
            "shipping_address": "地址",
        })

        resp = await client.get("/api/v1/commerce/orders", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        assert data[0]["status"] == "pending"
        assert data[0]["item_count"] == 1

    async def test_list_orders_filter_by_status(self, client, auth_headers, seed_product):
        # Create order
        await client.post("/api/v1/commerce/cart/items", headers=auth_headers, json={
            "product_id": seed_product.id, "quantity": 1,
        })
        order_resp = await client.post("/api/v1/commerce/orders", headers=auth_headers, json={})
        order_id = order_resp.json()["id"]

        # Filter by pending
        resp = await client.get("/api/v1/commerce/orders?status=pending", headers=auth_headers)
        assert resp.status_code == 200
        assert any(o["id"] == order_id for o in resp.json())

        # Filter by shipped (should be empty)
        resp2 = await client.get("/api/v1/commerce/orders?status=shipped", headers=auth_headers)
        assert resp2.status_code == 200
        assert resp2.json() == []

    async def test_get_order_by_id(self, client, auth_headers, seed_product):
        await client.post("/api/v1/commerce/cart/items", headers=auth_headers, json={
            "product_id": seed_product.id, "quantity": 1,
        })
        order_resp = await client.post("/api/v1/commerce/orders", headers=auth_headers, json={
            "shipping_address": "北京市朝阳区",
            "contact_phone": "13800138000",
        })
        order_id = order_resp.json()["id"]

        resp = await client.get(f"/api/v1/commerce/orders/{order_id}", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == order_id
        assert data["shipping_address"] == "北京市朝阳区"
        assert data["contact_phone"] == "13800138000"
        assert len(data["items"]) == 1

    async def test_get_order_not_found(self, client, auth_headers):
        resp = await client.get("/api/v1/commerce/orders/99999", headers=auth_headers)
        assert resp.status_code == 404

    async def test_reorder(self, client, auth_headers, seed_product, session):
        # Create and order, then reorder
        await client.post("/api/v1/commerce/cart/items", headers=auth_headers, json={
            "product_id": seed_product.id, "quantity": 2,
        })
        order_resp = await client.post("/api/v1/commerce/orders", headers=auth_headers, json={})
        order_id = order_resp.json()["id"]

        session.expire_all()
        # Reorder
        resp = await client.post(f"/api/v1/commerce/orders/{order_id}/reorder", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["product_name"] == "测试商品"
        assert data["items"][0]["quantity"] == 2

    async def test_reorder_order_not_found(self, client, auth_headers):
        resp = await client.post("/api/v1/commerce/orders/99999/reorder", headers=auth_headers)
        assert resp.status_code == 404

    async def test_cart_becomes_empty_after_order(self, client, auth_headers, seed_product, session):
        """After creating an order, the cart should be cleared."""
        await client.post("/api/v1/commerce/cart/items", headers=auth_headers, json={
            "product_id": seed_product.id, "quantity": 1,
        })
        await client.post("/api/v1/commerce/orders", headers=auth_headers, json={})

        session.expire_all()
        cart = await client.get("/api/v1/commerce/cart", headers=auth_headers)
        assert cart.json()["items"] == []

    async def test_order_stock_decrement(self, client, auth_headers, seed_product, session):
        """Stock should decrease when an order is placed."""
        initial_stock = seed_product.stock
        await client.post("/api/v1/commerce/cart/items", headers=auth_headers, json={
            "product_id": seed_product.id, "quantity": 3,
        })
        await client.post("/api/v1/commerce/orders", headers=auth_headers, json={})

        # Refresh product and check stock
        await session.refresh(seed_product)
        assert seed_product.stock == initial_stock - 3

    async def test_cancel_pending_order(self, client, auth_headers, seed_product, session):
        """Cancel a pending order restores stock."""
        initial_stock = seed_product.stock
        await client.post("/api/v1/commerce/cart/items", headers=auth_headers, json={
            "product_id": seed_product.id, "quantity": 2,
        })
        order_resp = await client.post("/api/v1/commerce/orders", headers=auth_headers, json={})
        order_id = order_resp.json()["id"]

        resp = await client.post(f"/api/v1/commerce/orders/{order_id}/cancel", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "cancelled"

        await session.refresh(seed_product)
        assert seed_product.stock == initial_stock  # stock restored

    async def test_cancel_non_pending_order(self, client, auth_headers, seed_product):
        """Cannot cancel an order that is not pending or paid."""
        await client.post("/api/v1/commerce/cart/items", headers=auth_headers, json={
            "product_id": seed_product.id, "quantity": 1,
        })
        order_resp = await client.post("/api/v1/commerce/orders", headers=auth_headers, json={})
        order_id = order_resp.json()["id"]

        # First transition to completed
        await client.patch(f"/api/v1/commerce/orders/{order_id}/status", headers=auth_headers, json={
            "status": "paid",
        })
        await client.patch(f"/api/v1/commerce/orders/{order_id}/status", headers=auth_headers, json={
            "status": "shipped",
        })
        await client.patch(f"/api/v1/commerce/orders/{order_id}/status", headers=auth_headers, json={
            "status": "completed",
        })

        # Now try to cancel
        resp = await client.post(f"/api/v1/commerce/orders/{order_id}/cancel", headers=auth_headers)
        assert resp.status_code == 400

    async def test_cancel_order_not_found(self, client, auth_headers):
        resp = await client.post("/api/v1/commerce/orders/99999/cancel", headers=auth_headers)
        assert resp.status_code == 404

    async def test_update_order_status_valid(self, client, auth_headers, seed_product):
        await client.post("/api/v1/commerce/cart/items", headers=auth_headers, json={
            "product_id": seed_product.id, "quantity": 1,
        })
        order_resp = await client.post("/api/v1/commerce/orders", headers=auth_headers, json={})
        order_id = order_resp.json()["id"]

        resp = await client.patch(f"/api/v1/commerce/orders/{order_id}/status", headers=auth_headers, json={
            "status": "paid",
        })
        assert resp.status_code == 200
        assert resp.json()["status"] == "paid"

        resp = await client.patch(f"/api/v1/commerce/orders/{order_id}/status", headers=auth_headers, json={
            "status": "shipped",
        })
        assert resp.status_code == 200
        assert resp.json()["status"] == "shipped"

    async def test_update_order_status_invalid_transition(self, client, auth_headers, seed_product):
        await client.post("/api/v1/commerce/cart/items", headers=auth_headers, json={
            "product_id": seed_product.id, "quantity": 1,
        })
        order_resp = await client.post("/api/v1/commerce/orders", headers=auth_headers, json={})
        order_id = order_resp.json()["id"]

        # Cannot go from pending to completed directly
        resp = await client.patch(f"/api/v1/commerce/orders/{order_id}/status", headers=auth_headers, json={
            "status": "completed",
        })
        assert resp.status_code == 400

    async def test_update_order_status_not_found(self, client, auth_headers):
        resp = await client.patch("/api/v1/commerce/orders/99999/status", headers=auth_headers, json={
            "status": "paid",
        })
        assert resp.status_code == 404

    async def test_unauthorized_access(self, client):
        endpoints = [
            ("GET", "/api/v1/commerce/cart"),
            ("POST", "/api/v1/commerce/cart/items"),
            ("DELETE", "/api/v1/commerce/cart"),
            ("POST", "/api/v1/commerce/orders"),
            ("GET", "/api/v1/commerce/orders"),
        ]
        for method, path in endpoints:
            if method == "GET":
                resp = await client.get(path)
            elif method == "POST":
                resp = await client.post(path, json={})
            elif method == "DELETE":
                resp = await client.delete(path)
            assert resp.status_code == 401, f"{method} {path} should return 401"
