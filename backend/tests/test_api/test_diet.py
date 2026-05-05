"""Tests for diet API: health profile, meal records, diet plans."""
import pytest


class TestHealthProfile:
    async def test_get_profile_not_found(self, client, auth_headers):
        resp = await client.get("/api/v1/diet/profile", headers=auth_headers)
        assert resp.status_code == 404

    async def test_create_and_get_profile(self, client, auth_headers):
        resp = await client.put("/api/v1/diet/profile", headers=auth_headers, json={
            "height": 175, "weight": 70, "age": 28, "gender": "male",
            "allergies": ["花生"], "diet_goals": ["weight_loss"],
            "dietary_restrictions": [], "chronic_conditions": [],
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["height"] == 175
        assert "花生" in data["allergies"]

        resp2 = await client.get("/api/v1/diet/profile", headers=auth_headers)
        assert resp2.status_code == 200
        assert resp2.json()["height"] == 175


class TestMealRecords:
    async def test_create_meal(self, client, auth_headers):
        resp = await client.post("/api/v1/diet/meals", headers=auth_headers, json={
            "date": "2026-05-04",
            "meal_type": "lunch",
            "foods": [{"name": "米饭", "amount": "一碗", "calories": 200}],
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["meal_type"] == "lunch"
        assert data["foods"][0]["name"] == "米饭"

    async def test_list_meals(self, client, auth_headers):
        await client.post("/api/v1/diet/meals", headers=auth_headers, json={
            "date": "2026-05-04", "meal_type": "breakfast",
            "foods": [{"name": "面包", "amount": "两片"}],
        })
        resp = await client.get("/api/v1/diet/meals?meal_date=2026-05-04", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1

    async def test_delete_meal(self, client, auth_headers):
        create = await client.post("/api/v1/diet/meals", headers=auth_headers, json={
            "date": "2026-05-04", "meal_type": "dinner",
            "foods": [{"name": "面", "amount": "一碗"}],
        })
        meal_id = create.json()["id"]

        resp = await client.delete(f"/api/v1/diet/meals/{meal_id}", headers=auth_headers)
        assert resp.status_code == 204


class TestDietPlans:
    async def test_list_diet_plans_empty(self, client, auth_headers):
        resp = await client.get("/api/v1/diet/plans", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_get_diet_plan_not_found(self, client, auth_headers):
        resp = await client.get("/api/v1/diet/plans/9999", headers=auth_headers)
        assert resp.status_code == 404
