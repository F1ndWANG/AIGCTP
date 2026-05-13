"""Tests for restaurant recommendation API."""


class TestRestaurantRecommend:
    async def test_recommend_success(self, client, auth_headers):
        resp = await client.post("/api/v1/restaurant/recommend", headers=auth_headers, json={
            "city": "成都",
            "cuisine": "川菜",
            "dietary_restrictions": ["不吃辣"],
            "session_id": "restaurant-api-session",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "response" in data
        assert data["city"] == "成都"
        # Mock returns restaurant data
        assert "restaurants" in data
        assert "recommendation_id" in data

        saved = await client.get(
            "/api/v1/restaurant/recommendations?session_id=restaurant-api-session",
            headers=auth_headers,
        )
        assert saved.status_code == 200
        assert len(saved.json()) == 1

    async def test_recommend_without_cuisine(self, client, auth_headers):
        resp = await client.post("/api/v1/restaurant/recommend", headers=auth_headers, json={
            "city": "北京",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["city"] == "北京"

    async def test_recommend_uses_cuisine_when_map_has_no_result(self, client, auth_headers, monkeypatch):
        async def mock_empty_restaurants(*args, **kwargs):
            return []

        monkeypatch.setattr("app.services.amap.amap_service.search_restaurants", mock_empty_restaurants)
        resp = await client.post("/api/v1/restaurant/recommend", headers=auth_headers, json={
            "city": "北京",
            "cuisine": "湘菜",
        })

        assert resp.status_code == 200
        data = resp.json()
        assert data["restaurants"]
        assert "湘菜" in data["restaurants"][0]["category"]

    async def test_recommend_unauthorized(self, client):
        resp = await client.post("/api/v1/restaurant/recommend", json={
            "city": "成都",
        })
        assert resp.status_code == 401

    async def test_select_recommendation_restaurant(self, client, auth_headers):
        resp = await client.post("/api/v1/restaurant/recommend", headers=auth_headers, json={
            "city": "北京",
            "session_id": "select-session",
        })
        recommendation_id = resp.json()["recommendation_id"]
        restaurant = resp.json()["restaurants"][0]

        selected = await client.post(
            f"/api/v1/restaurant/recommendations/{recommendation_id}/select",
            headers=auth_headers,
            json={"restaurant": restaurant},
        )
        assert selected.status_code == 200
        assert selected.json()["selected_restaurant"]["name"] == restaurant["name"]


class TestRestaurantNearby:
    async def test_nearby_success(self, client, auth_headers):
        resp = await client.post("/api/v1/restaurant/nearby", headers=auth_headers, json={
            "lat": 30.57,
            "lng": 104.07,
            "radius": 1000,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "response" in data
        assert "restaurants" in data

    async def test_nearby_with_types(self, client, auth_headers):
        resp = await client.post("/api/v1/restaurant/nearby", headers=auth_headers, json={
            "lat": 30.57,
            "lng": 104.07,
            "radius": 2000,
            "types": "美食",
        })
        assert resp.status_code == 200

    async def test_nearby_unauthorized(self, client):
        resp = await client.post("/api/v1/restaurant/nearby", json={
            "lat": 30.57,
            "lng": 104.07,
        })
        assert resp.status_code == 401
