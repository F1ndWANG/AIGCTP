"""Tests for auth API: register and login."""


class TestRegister:
    async def test_register_success(self, client):
        resp = await client.post("/api/v1/auth/register", json={
            "username": "newuser",
            "password": "Pass1234",
            "display_name": "New User",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert "access_token" in data
        assert data["user"]["username"] == "newuser"

    async def test_register_duplicate_username(self, client):
        await client.post("/api/v1/auth/register", json={
            "username": "dupuser", "password": "Pass1234",
        })
        resp = await client.post("/api/v1/auth/register", json={
            "username": "dupuser", "password": "Pass4567",
        })
        assert resp.status_code == 400


class TestLogin:
    async def test_login_success(self, client):
        await client.post("/api/v1/auth/register", json={
            "username": "loginuser", "password": "Pass1234",
        })
        resp = await client.post("/api/v1/auth/login", json={
            "username": "loginuser", "password": "Pass1234",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data

    async def test_login_invalid_password(self, client):
        await client.post("/api/v1/auth/register", json={
            "username": "loginfail", "password": "Correct1",
        })
        resp = await client.post("/api/v1/auth/login", json={
            "username": "loginfail", "password": "Wrong1",
        })
        assert resp.status_code == 401

    async def test_login_nonexistent_user(self, client):
        resp = await client.post("/api/v1/auth/login", json={
            "username": "noone", "password": "Nopass1",
        })
        assert resp.status_code == 401


class TestLogout:
    async def test_logout_returns_200(self, client):
        # Register and login
        reg = await client.post("/api/v1/auth/register", json={
            "username": "logoutuser", "password": "Pass1234",
        })
        assert reg.status_code == 201
        token = reg.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Logout
        logout_resp = await client.post("/api/v1/auth/logout", headers=headers)
        assert logout_resp.status_code == 200

    async def test_logout_without_token_returns_401(self, client):
        resp = await client.post("/api/v1/auth/logout")
        assert resp.status_code == 401  # no auth header
