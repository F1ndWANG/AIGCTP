"""Tests for auth API: register and login."""
import pytest


class TestRegister:
    async def test_register_success(self, client):
        resp = await client.post("/api/v1/auth/register", json={
            "username": "newuser",
            "password": "pass123",
            "display_name": "New User",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert "access_token" in data
        assert data["user"]["username"] == "newuser"

    async def test_register_duplicate_username(self, client):
        await client.post("/api/v1/auth/register", json={
            "username": "dupuser", "password": "pass123",
        })
        resp = await client.post("/api/v1/auth/register", json={
            "username": "dupuser", "password": "pass456",
        })
        assert resp.status_code == 400


class TestLogin:
    async def test_login_success(self, client):
        await client.post("/api/v1/auth/register", json={
            "username": "loginuser", "password": "pass123",
        })
        resp = await client.post("/api/v1/auth/login", json={
            "username": "loginuser", "password": "pass123",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data

    async def test_login_invalid_password(self, client):
        await client.post("/api/v1/auth/register", json={
            "username": "loginfail", "password": "correct",
        })
        resp = await client.post("/api/v1/auth/login", json={
            "username": "loginfail", "password": "wrong",
        })
        assert resp.status_code == 401

    async def test_login_nonexistent_user(self, client):
        resp = await client.post("/api/v1/auth/login", json={
            "username": "noone", "password": "nopass",
        })
        assert resp.status_code == 401
