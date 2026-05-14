"""Tests for chat API: standard and streaming endpoints."""
import pytest
from sqlalchemy import select

from app.agents.supervisor import _classify_intent
from app.models.runtime import DomainEvent, TaskRun


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

    async def test_chat_records_task_and_domain_event(self, client, auth_headers, session):
        resp = await client.post("/api/v1/chat", headers=auth_headers, json={
            "message": "你好",
            "session_id": "runtime-chat-session",
        })
        assert resp.status_code == 200

        tasks = (
            await session.execute(
                select(TaskRun).where(TaskRun.session_id == "runtime-chat-session")
            )
        ).scalars().all()
        events = (
            await session.execute(
                select(DomainEvent).where(DomainEvent.session_id == "runtime-chat-session")
            )
        ).scalars().all()

        assert len(tasks) == 1
        assert tasks[0].status == "succeeded"
        assert any(event.event_type == "chat.completed" for event in events)

    async def test_chat_unauthorized(self, client):
        resp = await client.post("/api/v1/chat", json={"message": "你好"})
        assert resp.status_code == 401

    async def test_chat_product_recommendation_creates_catalog_items(self, client, auth_headers):
        resp = await client.post("/api/v1/chat", headers=auth_headers, json={
            "message": "帮我推荐旅行好物",
            "session_id": "product-session",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["products"]

        products = await client.get("/api/v1/commerce/products?keyword=旅行", headers=auth_headers)
        assert products.status_code == 200
        assert products.json()["total"] >= 1

    async def test_chat_auto_cart_adds_item(self, client, auth_headers):
        resp = await client.post("/api/v1/chat", headers=auth_headers, json={
            "message": "帮我加购雨伞",
            "session_id": "cart-session",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["cart_items"]

        cart = await client.get("/api/v1/commerce/cart", headers=auth_headers)
        assert cart.status_code == 200
        assert len(cart.json()["items"]) == 1

    async def test_chat_restaurant_recommendation_is_saved(self, client, auth_headers):
        resp = await client.post("/api/v1/chat", headers=auth_headers, json={
            "message": "推荐北京好吃的餐厅",
            "session_id": "restaurant-session",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["restaurants"]
        assert data["restaurant_recommendation_id"]

        saved = await client.get(
            "/api/v1/restaurant/recommendations?session_id=restaurant-session",
            headers=auth_headers,
        )
        assert saved.status_code == 200
        assert len(saved.json()) == 1

    async def test_existing_plan_natural_language_update_syncs_card(self, client, auth_headers):
        created = await client.post("/api/v1/chat", headers=auth_headers, json={
            "message": "北京二日游",
            "session_id": "travel-adjust-session",
        })
        assert created.status_code == 200
        plan = created.json()["travel_plan"]
        assert plan["id"]

        resp = await client.post("/api/v1/chat", headers=auth_headers, json={
            "message": "第二天下午加上什刹海和南锣鼓巷",
            "session_id": "travel-adjust-session",
            "travel_plan_id": plan["id"],
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "已将 什刹海, 南锣鼓巷 同步到行程卡" in data["message"]

        activities = data["travel_plan"]["itinerary"]["day_by_day"][1]["activities"]
        pois = [activity["poi"] for activity in activities]
        assert "什刹海" in pois
        assert "南锣鼓巷" in pois

    async def test_created_travel_plan_syncs_recommendation_catalog(self, client, auth_headers, session):
        from sqlalchemy import select
        from app.models.recommendation import RecommendationItem

        created = await client.post("/api/v1/chat", headers=auth_headers, json={
            "message": "北京一日游，想去天坛",
            "session_id": "travel-catalog-sync-session",
        })
        assert created.status_code == 200
        plan = created.json()["travel_plan"]

        result = await session.execute(
            select(RecommendationItem).where(
                RecommendationItem.domain == "travel",
                RecommendationItem.item_type == "travel_plan",
                RecommendationItem.source_id == str(plan["id"]),
            )
        )
        item = result.scalar_one_or_none()
        assert item is not None
        assert item.city == "北京"

    async def test_adjusting_confirmed_plan_returns_to_draft(self, client, auth_headers):
        created = await client.post("/api/v1/chat", headers=auth_headers, json={
            "message": "北京二日游",
            "session_id": "confirmed-adjust-session",
        })
        assert created.status_code == 200
        plan = created.json()["travel_plan"]

        confirmed = await client.post(
            f"/api/v1/travel/plans/{plan['id']}/confirm",
            headers=auth_headers,
        )
        assert confirmed.status_code == 200
        assert confirmed.json()["status"] == "confirmed"

        adjusted = await client.post("/api/v1/chat", headers=auth_headers, json={
            "message": "第二天下午加上什刹海",
            "session_id": "confirmed-adjust-session",
            "travel_plan_id": plan["id"],
        })
        assert adjusted.status_code == 200
        assert adjusted.json()["travel_plan"]["status"] == "draft"

    async def test_new_trip_with_city_poi_keeps_city_and_card_poi(self, client, auth_headers):
        resp = await client.post("/api/v1/chat", headers=auth_headers, json={
            "message": "北京什刹海一日游",
            "session_id": "city-poi-session",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["travel_plan"]["destination"] == "北京"
        assert "已将 什刹海 同步到行程卡" in data["message"]

        activities = data["travel_plan"]["itinerary"]["day_by_day"][0]["activities"]
        pois = [activity["poi"] for activity in activities]
        assert "什刹海" in pois

    async def test_travel_adjust_remembers_and_replaces_excluded_related_pois(
        self,
        client,
        auth_headers,
        monkeypatch,
    ):
        async def fake_fetch_domain_data(*args, **kwargs):
            return (
                [
                    {"name": "天安门广场", "category": "景点"},
                    {"name": "天安门", "category": "景点"},
                    {"name": "故宫博物院", "category": "景点"},
                    {"name": "北海公园", "category": "景点"},
                    {"name": "景山公园", "category": "景点"},
                ],
                [],
                [],
                [{"condition": "晴", "temp_min": "10", "temp_max": "24"}],
                [],
            )

        attempts = {"count": 0}

        async def fake_chat_with_artifact(*args, **kwargs):
            attempts["count"] += 1
            if attempts["count"] == 1:
                return {
                    "text": "我会帮你调整行程。",
                    "artifact": {
                        "destination": "北京",
                        "days": 1,
                        "theme": "调整后的北京一日游",
                        "day_by_day": [
                            {
                                "day": 1,
                                "theme": "文化探索",
                                "activities": [
                                    {"time": "上午", "poi": "天安门广场", "duration": "2小时"},
                                    {"time": "下午", "poi": "北海公园", "duration": "2小时"},
                                ],
                                "meals": [],
                                "shopping": [],
                                "hotel": {},
                                "transport_tips": "",
                            }
                        ],
                    },
                }
            return {
                "text": "已避开天安门相关景点，改为北海公园和景山公园。",
                "artifact": {
                    "destination": "北京",
                    "days": 1,
                    "theme": "北京公园与古都漫步",
                    "day_by_day": [
                        {
                            "day": 1,
                            "theme": "北海景山漫步",
                            "activities": [
                                {"time": "上午", "poi": "北海公园", "duration": "2小时"},
                                {"time": "下午", "poi": "景山公园", "duration": "2小时"},
                            ],
                            "meals": [],
                            "shopping": [],
                            "hotel": {},
                            "transport_tips": "",
                        }
                    ],
                },
            }

        monkeypatch.setattr("app.agents.travel_agent._fetch_domain_data", fake_fetch_domain_data)
        monkeypatch.setattr("app.services.llm.llm_service.chat_with_artifact", fake_chat_with_artifact)

        created = await client.post("/api/v1/chat", headers=auth_headers, json={
            "message": "规划北京一日游",
            "session_id": "avoid-tiananmen-session",
        })
        assert created.status_code == 200
        plan = created.json()["travel_plan"]

        adjusted = await client.post("/api/v1/chat", headers=auth_headers, json={
            "message": "我不想去天安门，帮我换别的",
            "session_id": "avoid-tiananmen-session",
            "travel_plan_id": plan["id"],
        })
        assert adjusted.status_code == 200
        data = adjusted.json()
        activities = data["travel_plan"]["itinerary"]["day_by_day"][0]["activities"]
        pois = [activity["poi"] for activity in activities]

        assert "天安门" not in "".join(pois)
        assert "北海公园" in pois
        assert "景山公园" in pois
        assert "已根据你的要求避开" in data["message"]

        session_detail = await client.get(
            "/api/v1/chat/sessions/avoid-tiananmen-session",
            headers=auth_headers,
        )
        assert session_detail.status_code == 200
        memory = session_detail.json()["context"]["travel_memory"]
        assert "天安门广场" in memory["avoid_pois"]


class TestChatIntentClassification:
    @pytest.mark.parametrize("message", [
        "我想去什刹海",
        "第二天下午加上南锣鼓巷",
        "把故宫换成颐和园",
        "不要天安门，想去北海公园",
        "上午安排798艺术区",
        "这几个都玩过，换别的",
        "预算控制在1000以内",
        "行程太赶了，轻松一点",
    ])
    def test_existing_plan_adjustment_phrases(self, message):
        intent, _ = _classify_intent(message, has_travel_plan=True)
        assert intent == "travel_adjust"

    @pytest.mark.parametrize("message", [
        "帮我加购雨伞",
        "把防晒霜加入购物车",
        "帮我做一周减脂饮食计划",
        "推荐北京好吃的餐厅",
    ])
    def test_non_travel_actions_are_not_stolen_by_plan_adjustment(self, message):
        intent, _ = _classify_intent(message, has_travel_plan=True)
        assert intent != "travel_adjust"


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
