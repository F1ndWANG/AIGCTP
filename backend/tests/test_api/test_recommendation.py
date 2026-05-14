"""Tests for recommendation API and hybrid V2 behavior."""

import pytest


@pytest.fixture
async def recommendation_products(session):
    from app.models.commerce import Category, Product

    category = Category(name="旅行好物", description="旅行用品", icon="bag", sort_order=1)
    session.add(category)
    await session.flush()

    water_bottle = Product(
        name="轻量保温水杯",
        description="适合旅行和通勤的便携水杯",
        price=69.9,
        stock=100,
        unit="个",
        category_id=category.id,
        tags=["旅行", "便携", "水杯"],
        rating=4.9,
        status="active",
    )
    headphones = Product(
        name="降噪耳机",
        description="适合长途旅行和通勤",
        price=299,
        stock=100,
        unit="副",
        category_id=category.id,
        tags=["旅行", "数码", "降噪"],
        rating=4.7,
        status="active",
    )
    session.add_all([water_bottle, headphones])
    await session.commit()
    await session.refresh(water_bottle)
    await session.refresh(headphones)
    return water_bottle, headphones


class TestRecommendationEvents:
    async def test_track_event_requires_login(self, client):
        resp = await client.post("/api/v1/recommend/events", json={
            "domain": "commerce",
            "item_type": "product",
            "item_id": "1",
            "event_type": "click",
        })
        assert resp.status_code == 401

    async def test_track_event_success(self, client, auth_headers):
        resp = await client.post("/api/v1/recommend/events", headers=auth_headers, json={
            "domain": "commerce",
            "item_type": "product",
            "item_id": "1",
            "event_type": "click",
            "context": {"keyword": "旅行"},
        })
        assert resp.status_code == 201
        assert resp.json()["status"] == "recorded"

    async def test_invalid_event_type_returns_422(self, client, auth_headers):
        resp = await client.post("/api/v1/recommend/events", headers=auth_headers, json={
            "domain": "commerce",
            "item_type": "product",
            "item_id": "1",
            "event_type": "unknown",
        })
        assert resp.status_code == 422


class TestRecommendationFeed:
    async def test_cold_start_feed_returns_product_fallback(self, client, auth_headers, recommendation_products):
        resp = await client.get("/api/v1/recommend/feed?domain=commerce&limit=4", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["algorithm"] == "hybrid_v2"
        assert data["total"] >= 1
        assert data["items"][0]["domain"] == "commerce"
        assert data["items"][0]["impression_id"]
        assert data["items"][0]["rank"] == 1
        assert data["items"][0]["algorithm"] == "hybrid_v2"

    async def test_negative_feedback_filters_item(self, client, auth_headers, recommendation_products):
        water_bottle, _ = recommendation_products
        feedback = await client.post("/api/v1/recommend/feedback", headers=auth_headers, json={
            "domain": "commerce",
            "item_type": "product",
            "item_id": water_bottle.id,
            "feedback": "hide",
        })
        assert feedback.status_code == 201

        resp = await client.get("/api/v1/recommend/feed?domain=commerce&limit=10", headers=auth_headers)
        assert resp.status_code == 200
        ids = {item["item_id"] for item in resp.json()["items"]}
        assert str(water_bottle.id) not in ids

    async def test_refresh_embeddings_uses_local_fallback(self, client, auth_headers, recommendation_products):
        resp = await client.post("/api/v1/recommend/refresh-embeddings", headers=auth_headers, json={
            "domain": "commerce",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["model"] == "local-token-vector"
        assert data["refreshed"] >= 1

    async def test_profile_endpoint_exposes_interest_terms(self, client, auth_headers):
        tracked = await client.post("/api/v1/recommend/events", headers=auth_headers, json={
            "domain": "travel",
            "item_type": "travel_note",
            "item_id": "beijing-note",
            "event_type": "click",
            "context": {"destination": "北京", "tags": ["citywalk", "美食"]},
        })
        assert tracked.status_code == 201

        resp = await client.get("/api/v1/recommend/profile", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["algorithm"] == "hybrid_v2"
        assert data["event_count"] >= 1
        terms = {item["term"] for item in data["top_terms"]}
        assert "北京" in terms or "美食" in terms or "citywalk" in terms

    async def test_batch_events_and_evaluation(self, client, auth_headers, recommendation_products):
        feed = await client.get("/api/v1/recommend/feed?domain=commerce&limit=2", headers=auth_headers)
        item = feed.json()["items"][0]
        batch = await client.post("/api/v1/recommend/events/batch", headers=auth_headers, json={
            "events": [
                {
                    "domain": item["domain"],
                    "item_type": item["item_type"],
                    "item_id": item["item_id"],
                    "event_type": "view",
                    "impression_id": item["impression_id"],
                    "context": {"rank": item["rank"]},
                },
                {
                    "domain": item["domain"],
                    "item_type": item["item_type"],
                    "item_id": item["item_id"],
                    "event_type": "click",
                    "impression_id": item["impression_id"],
                    "context": {"rank": item["rank"]},
                },
            ]
        })
        assert batch.status_code == 201
        assert batch.json()["count"] == 2

        evaluation = await client.get("/api/v1/recommend/evaluation?domain=commerce", headers=auth_headers)
        assert evaluation.status_code == 200
        assert evaluation.json()["impressions"] >= 1
        assert evaluation.json()["clicks"] >= 1

    async def test_catalog_rebuild_and_feature_refresh(self, client, auth_headers, recommendation_products):
        rebuild = await client.post("/api/v1/recommend/catalog/rebuild", headers=auth_headers, json={"domain": "commerce"})
        assert rebuild.status_code == 200
        assert rebuild.json()["synced"] >= 1

        feed = await client.get("/api/v1/recommend/feed?domain=commerce&limit=2", headers=auth_headers)
        item = feed.json()["items"][0]
        await client.post("/api/v1/recommend/events", headers=auth_headers, json={
            "domain": "commerce",
            "item_type": "product",
            "item_id": item["item_id"],
            "event_type": "add_cart",
            "impression_id": item["impression_id"],
        })
        refresh = await client.post("/api/v1/recommend/features/refresh", headers=auth_headers, json={"domain": "commerce"})
        assert refresh.status_code == 200
        assert refresh.json()["snapshots"] >= 1

        ranked = await client.get("/api/v1/recommend/feed?domain=commerce&limit=2", headers=auth_headers)
        assert any("feature_quality" in item["source_reasons"] for item in ranked.json()["items"])

    async def test_behavior_cooccurrence_boosts_collaborative_candidate(self, client, auth_headers, session):
        from app.core.security import hash_password
        from app.models.commerce import Category, Product
        from app.models.recommendation import RecommendationEvent
        from app.models.user import User
        from app.services.recommendation.catalog import sync_product_item

        category = Category(name="旅行装备", description="旅行用品", icon="bag", sort_order=1)
        session.add(category)
        await session.flush()
        seed = Product(
            name="城市徒步背包",
            description="适合城市旅行",
            price=129,
            stock=100,
            unit="个",
            category_id=category.id,
            tags=["城市", "旅行"],
            rating=4.2,
            status="active",
        )
        collab = Product(
            name="轻便折叠雨伞",
            description="常和城市徒步背包一起购买",
            price=49,
            stock=100,
            unit="把",
            category_id=category.id,
            tags=["雨具"],
            rating=4.9,
            status="active",
        )
        unrelated = Product(
            name="厨房收纳盒",
            description="厨房整理工具",
            price=39,
            stock=100,
            unit="个",
            category_id=category.id,
            tags=["厨房"],
            rating=5.0,
            status="active",
        )
        session.add_all([seed, collab, unrelated])
        await session.flush()
        for product in (seed, collab, unrelated):
            await sync_product_item(session, product)

        peer = User(
            username="peer-user",
            hashed_password=hash_password("testpass123"),
            display_name="Peer User",
        )
        session.add(peer)
        await session.flush()
        session.add_all([
            RecommendationEvent(user_id=1, domain="commerce", item_type="product", item_id=str(seed.id), event_type="add_cart", weight=4),
            RecommendationEvent(user_id=peer.id, domain="commerce", item_type="product", item_id=str(seed.id), event_type="add_cart", weight=4),
            RecommendationEvent(user_id=peer.id, domain="commerce", item_type="product", item_id=str(collab.id), event_type="order", weight=6),
        ])
        await session.commit()

        feed = await client.get("/api/v1/recommend/feed?domain=commerce&limit=10", headers=auth_headers)
        assert feed.status_code == 200
        items = feed.json()["items"]
        collab_item = next(item for item in items if item["item_id"] == str(collab.id))
        unrelated_item = next(item for item in items if item["item_id"] == str(unrelated.id))
        assert "collaborative_recall" in collab_item["source_reasons"]
        assert collab_item["score"] > unrelated_item["score"]
