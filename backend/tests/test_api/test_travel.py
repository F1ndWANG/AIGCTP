"""Tests for travel plans API."""
import pytest


class TestListPlans:
    async def test_list_plans_empty(self, client, auth_headers):
        resp = await client.get("/api/v1/travel/plans", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []


class TestGetPlan:
    async def test_get_plan_not_found(self, client, auth_headers):
        resp = await client.get("/api/v1/travel/plans/9999", headers=auth_headers)
        assert resp.status_code == 404


class TestDeletePlan:
    async def test_delete_plan_not_found(self, client, auth_headers):
        resp = await client.delete("/api/v1/travel/plans/9999", headers=auth_headers)
        assert resp.status_code == 404
