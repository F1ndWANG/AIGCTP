"""Tests for users API: profile and preferences."""
import pytest


class TestGetMe:
    async def test_get_me_authenticated(self, client, auth_headers):
        resp = await client.get("/api/v1/users/me", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["username"] == "testuser"

    async def test_get_me_unauthorized(self, client):
        resp = await client.get("/api/v1/users/me")
        assert resp.status_code == 401


class TestPreferences:
    async def test_update_preferences(self, client, auth_headers):
        resp = await client.put(
            "/api/v1/users/me/preferences",
            headers=auth_headers,
            json={"preferences": {"theme": "light", "lang": "en"}},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["preferences"]["theme"] == "light"
