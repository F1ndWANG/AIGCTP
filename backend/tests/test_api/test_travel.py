"""Tests for travel plans API."""


class TestListPlans:
    async def test_list_plans_empty(self, client, auth_headers):
        resp = await client.get("/api/v1/travel/plans", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []


class TestGetPlan:
    async def test_get_plan_not_found(self, client, auth_headers):
        resp = await client.get("/api/v1/travel/plans/9999", headers=auth_headers)
        assert resp.status_code == 404


class TestConfirmPlan:
    async def test_confirm_plan_marks_final(self, client, auth_headers):
        created = await client.post("/api/v1/chat", headers=auth_headers, json={
            "message": "北京一日游",
            "session_id": "confirm-travel-session",
        })
        assert created.status_code == 200
        plan = created.json()["travel_plan"]
        assert plan["status"] == "draft"

        resp = await client.post(
            f"/api/v1/travel/plans/{plan['id']}/confirm",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "confirmed"

    async def test_confirm_plan_not_found(self, client, auth_headers):
        resp = await client.post("/api/v1/travel/plans/9999/confirm", headers=auth_headers)
        assert resp.status_code == 404


class TestDeletePlan:
    async def test_delete_plan_not_found(self, client, auth_headers):
        resp = await client.delete("/api/v1/travel/plans/9999", headers=auth_headers)
        assert resp.status_code == 404
