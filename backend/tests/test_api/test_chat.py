"""Tests for chat API: standard and streaming endpoints."""
import pytest


class TestChat:
    async def test_chat_general(self, client, auth_headers):
        resp = await client.post("/api/v1/chat", headers=auth_headers, json={
            "message": "你好",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "session_id" in data
        assert "message" in data

    async def test_chat_with_session_id(self, client, auth_headers):
        first = await client.post("/api/v1/chat", headers=auth_headers, json={
            "message": "你好",
        })
        sid = first.json()["session_id"]
        resp = await client.post("/api/v1/chat", headers=auth_headers, json={
            "message": "再聊",
            "session_id": sid,
        })
        assert resp.status_code == 200
        assert resp.json()["session_id"] == sid

    async def test_chat_unauthorized(self, client):
        resp = await client.post("/api/v1/chat", json={"message": "你好"})
        assert resp.status_code == 401


class TestChatStream:
    async def test_chat_stream_returns_sse(self, client, auth_headers):
        resp = await client.post("/api/v1/chat/stream", headers=auth_headers, json={
            "message": "你好",
        })
        assert resp.status_code == 200
        assert resp.headers.get("content-type", "").startswith("text/event-stream")

    async def test_chat_stream_unauthorized(self, client):
        resp = await client.post("/api/v1/chat/stream", json={"message": "你好"})
        assert resp.status_code == 401
