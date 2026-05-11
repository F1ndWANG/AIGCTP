"""Tests for route planning API."""


class TestRoute:
    async def test_route_with_coordinates(self, client, auth_headers):
        resp = await client.post("/api/v1/route", headers=auth_headers, json={
            "destination_name": "宽窄巷子",
            "destination_lat": 30.67,
            "destination_lng": 104.05,
            "origin_lat": 30.57,
            "origin_lng": 104.07,
            "mode": "transit",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "distance" in data
        assert "steps" in data
        assert data["destination_name"] == "宽窄巷子"

    async def test_route_geocode_fallback(self, client, auth_headers):
        resp = await client.post("/api/v1/route", headers=auth_headers, json={
            "destination_name": "宽窄巷子",
            "origin_lat": 30.57,
            "origin_lng": 104.07,
            "city": "成都",
            "mode": "driving",
        })
        assert resp.status_code == 200
        assert "distance" in resp.json()

    async def test_route_missing_auth(self, client):
        resp = await client.post("/api/v1/route", json={
            "destination_name": "宽窄巷子",
            "origin_lat": 30.57, "origin_lng": 104.07,
        })
        assert resp.status_code == 401
