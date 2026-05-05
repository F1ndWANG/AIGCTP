"""Tests for feedback API: submit feedback, stats, analytics."""
import pytest


class TestSubmitFeedback:
    async def test_submit_like(self, client, auth_headers):
        resp = await client.post("/api/v1/feedback", headers=auth_headers, json={
            "content_type": "travel_plan",
            "feedback": "like",
            "message_id": "msg_001",
            "content_snapshot": {"destination": "成都", "days": 3},
            "context": {"session_id": "sess_001"},
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "ok"
        assert "id" in data

    async def test_submit_dislike(self, client, auth_headers):
        resp = await client.post("/api/v1/feedback", headers=auth_headers, json={
            "content_type": "diet",
            "feedback": "dislike",
            "message_id": "msg_002",
        })
        assert resp.status_code == 201
        assert resp.json()["status"] == "ok"

    async def test_submit_invalid_feedback(self, client, auth_headers):
        resp = await client.post("/api/v1/feedback", headers=auth_headers, json={
            "content_type": "travel_plan",
            "feedback": "invalid_value",
        })
        assert resp.status_code == 400

    async def test_submit_unauthorized(self, client):
        resp = await client.post("/api/v1/feedback", json={
            "content_type": "travel_plan",
            "feedback": "like",
        })
        assert resp.status_code == 401


class TestFeedbackStats:
    async def test_stats_empty(self, client, auth_headers):
        resp = await client.get("/api/v1/feedback/stats", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_stats_with_data(self, client, auth_headers):
        # Submit likes and dislikes
        for content_type in ["travel_plan", "diet"]:
            await client.post("/api/v1/feedback", headers=auth_headers, json={
                "content_type": content_type,
                "feedback": "like",
            })
            await client.post("/api/v1/feedback", headers=auth_headers, json={
                "content_type": content_type,
                "feedback": "dislike",
            })
        # Extra like for travel_plan
        await client.post("/api/v1/feedback", headers=auth_headers, json={
            "content_type": "travel_plan",
            "feedback": "like",
        })

        resp = await client.get("/api/v1/feedback/stats", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        stats_map = {s["content_type"]: s for s in data}

        assert stats_map["travel_plan"]["likes"] == 2
        assert stats_map["travel_plan"]["dislikes"] == 1
        assert stats_map["diet"]["likes"] == 1
        assert stats_map["diet"]["dislikes"] == 1

    async def test_stats_isolated_per_user(self, client, auth_headers, session):
        """Another user's feedback should not appear in this user's stats."""
        # Submit feedback for current user
        await client.post("/api/v1/feedback", headers=auth_headers, json={
            "content_type": "commerce",
            "feedback": "like",
        })

        resp = await client.get("/api/v1/feedback/stats", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        commerce_stats = next((s for s in data if s["content_type"] == "commerce"), None)
        assert commerce_stats is not None
        assert commerce_stats["likes"] == 1


class TestAnalyticsSummary:
    async def test_analytics_empty(self, client, auth_headers):
        resp = await client.get("/api/v1/feedback/analytics/summary", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_interactions"] == 0
        assert data["by_content_type"] == {}

    async def test_analytics_with_data(self, client, auth_headers):
        await client.post("/api/v1/feedback", headers=auth_headers, json={
            "content_type": "travel_plan", "feedback": "like",
        })
        await client.post("/api/v1/feedback", headers=auth_headers, json={
            "content_type": "travel_plan", "feedback": "like",
        })
        await client.post("/api/v1/feedback", headers=auth_headers, json={
            "content_type": "travel_plan", "feedback": "dislike",
        })
        await client.post("/api/v1/feedback", headers=auth_headers, json={
            "content_type": "diet", "feedback": "like",
        })

        resp = await client.get("/api/v1/feedback/analytics/summary", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_interactions"] == 4
        assert data["by_content_type"]["travel_plan"]["total"] == 3
        assert data["by_content_type"]["travel_plan"]["likes"] == 2
        assert data["by_content_type"]["travel_plan"]["dislikes"] == 1
        assert data["by_content_type"]["diet"]["total"] == 1
        assert data["by_content_type"]["diet"]["likes"] == 1
