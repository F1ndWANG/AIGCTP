"""Tests for restaurant recommendation API."""
import pytest


class TestRestaurantRecommend:
    async def test_recommend_success(self, client, auth_headers):
        resp = await client.post("/api/v1/restaurant/recommend", headers=auth_headers, json={
            "city": "成都",
            "cuisine": "川菜",
            "dietary_restrictions": ["不吃辣"],
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "response" in data
        assert data["city"] == "成都"
        # Mock returns restaurant data
        assert "restaurants" in data

    async def test_recommend_without_cuisine(self, client, auth_headers):
        resp = await client.post("/api/v1/restaurant/recommend", headers=auth_headers, json={
            "city": "北京",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["city"] == "北京"

    async def test_recommend_unauthorized(self, client):
        resp = await client.post("/api/v1/restaurant/recommend", json={
            "city": "成都",
        })
        assert resp.status_code == 401


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
