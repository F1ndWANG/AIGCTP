"""Tests for recommendation API and hybrid V1 fallback behavior."""

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
        assert data["algorithm"] == "hybrid_v1"
        assert data["total"] >= 1
        assert data["items"][0]["domain"] == "commerce"

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
        assert data["algorithm"] == "hybrid_v1"
        assert data["event_count"] >= 1
        terms = {item["term"] for item in data["top_terms"]}
        assert "北京" in terms or "美食" in terms or "citywalk" in terms
