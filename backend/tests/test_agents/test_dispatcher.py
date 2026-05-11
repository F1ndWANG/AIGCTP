"""Tests for dispatcher — intent routing and helper functions."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.agents.dispatcher import (
    AgentDispatcher,
    _is_plan_query,
    _answer_plan_query,
    thinking_label_for_intent,
)


class TestThinkingLabel:
    def test_known_intents_have_labels(self):
        for intent in ["travel_plan", "travel_adjust", "travel_query",
                       "diet_recommend", "diet_log", "diet_analyze",
                       "restaurant_recommend", "commerce_recommend",
                       "auto_cart", "quick_reorder"]:
            label = thinking_label_for_intent(intent)
            assert label
            assert label != "正在处理..."

    def test_unknown_intent_falls_back(self):
        assert thinking_label_for_intent("nonexistent") == "正在处理..."
        assert thinking_label_for_intent("random") == "正在处理..."


class TestIsPlanQuery:
    def test_query_keywords_detected(self):
        assert _is_plan_query("今天有什么安排")
        assert _is_plan_query("明天去哪")
        assert _is_plan_query("第三天怎么玩")
        assert _is_plan_query("行程是什么")
        assert _is_plan_query("有什么好玩的")

    def test_adjust_keywords_override_query(self):
        # Adjust keywords take precedence — these are NOT queries
        assert not _is_plan_query("换一个景点")
        assert not _is_plan_query("改一下行程")
        assert not _is_plan_query("去掉故宫")
        assert not _is_plan_query("不想去天坛")

    def test_neither_query_nor_adjust(self):
        assert not _is_plan_query("你好")
        assert not _is_plan_query("推荐餐厅")
        assert not _is_plan_query("帮我买把伞")


class TestAnswerPlanQuery:
    def test_query_specific_day(self):
        plan = {
            "destination": "北京",
            "days": 3,
            "itinerary": {
                "day_by_day": [
                    {
                        "day": 1, "theme": "文化探索",
                        "weather": {"condition": "晴", "temp_min": "10", "temp_max": "20"},
                        "activities": [{"time": "09:00", "poi": "故宫", "duration": "3h"}],
                        "meals": [],
                    },
                    {
                        "day": 2, "theme": "历史之旅",
                        "weather": {},
                        "activities": [{"time": "10:00", "poi": "长城", "duration": "4h"}],
                        "meals": [],
                    },
                    {
                        "day": 3, "theme": "休闲日",
                        "weather": {},
                        "activities": [],
                        "meals": [],
                    },
                ]
            },
        }
        result = _answer_plan_query("第一天去哪", plan)
        assert "第1天" in result["response"]
        assert "故宫" in result["response"]

    def test_query_no_specific_day_shows_all(self):
        plan = {
            "destination": "上海",
            "days": 1,
            "itinerary": {
                "day_by_day": [
                    {
                        "day": 1, "theme": "都市观光",
                        "weather": {"condition": "多云", "temp_min": "15", "temp_max": "25"},
                        "activities": [{"time": "上午", "poi": "外滩", "duration": "2h"}],
                        "meals": [{"type": "午餐", "restaurant": "小笼包店", "recommendation": "小笼包"}],
                    },
                ]
            },
        }
        result = _answer_plan_query("今天有什么安排", plan)
        assert "上海" in result["response"]
        assert "外滩" in result["response"]
        # Meals only shown for specific day queries, not "all days" overview

    def test_query_specific_day_shows_meals(self):
        plan = {
            "destination": "上海",
            "days": 1,
            "itinerary": {
                "day_by_day": [
                    {
                        "day": 1, "theme": "都市观光",
                        "weather": {},
                        "activities": [],
                        "meals": [{"type": "午餐", "restaurant": "小笼包店", "recommendation": "小笼包"}],
                    },
                ]
            },
        }
        result = _answer_plan_query("第一天去哪", plan)
        assert "小笼包店" in result["response"]

    def test_query_day_out_of_range(self):
        plan = {"destination": "北京", "days": 1, "itinerary": {"day_by_day": []}}
        result = _answer_plan_query("第五天", plan)
        # Falls back to showing all days (empty list)
        assert "北京" in result["response"]


class TestDispatcherDispatch:
    @pytest.fixture
    def dispatcher(self):
        return AgentDispatcher()

    @pytest.fixture
    def base_kwargs(self):
        return {
            "intent": "general_chat",
            "extracted": {},
            "user_message": "你好",
            "messages": [{"role": "user", "content": "你好"}],
            "context": {},
            "user_id": 1,
            "db": AsyncMock(),
        }

    async def test_clarification_intent(self, dispatcher, base_kwargs):
        base_kwargs["intent"] = "clarification"
        base_kwargs["extracted"] = {"question": "你想去哪个城市？"}
        result = await dispatcher.dispatch(**base_kwargs)
        assert result["response"] == "你想去哪个城市？"

    async def test_clarification_default_question(self, dispatcher, base_kwargs):
        base_kwargs["intent"] = "clarification"
        result = await dispatcher.dispatch(**base_kwargs)
        assert "请提供更多信息" in result["response"]

    async def test_travel_plan_dispatch(self, dispatcher, base_kwargs):
        base_kwargs["intent"] = "travel_plan"
        base_kwargs["extracted"] = {"destination": "北京", "days": 3}
        with patch("app.agents.dispatcher.travel_agent.plan_trip", new_callable=AsyncMock) as mock_plan, \
             patch("app.agents.dispatcher.cross_domain_composer.merge", new_callable=AsyncMock) as mock_merge:
            mock_plan.return_value = type("Result", (), {
                "response": "这里是你的北京3日游行程",
                "travel_plan": {"destination": "北京", "days": 3},
                "to_legacy": lambda self: {"response": self.response, "travel_plan": self.travel_plan},
            })()
            mock_merge.return_value = {"response": "行程已生成", "travel_plan": {"destination": "北京", "days": 3}}
            result = await dispatcher.dispatch(**base_kwargs)
            assert result["response"]
            assert "travel_plan" in result

    async def test_travel_query_with_plan(self, dispatcher, base_kwargs):
        base_kwargs["intent"] = "travel_query"
        base_kwargs["context"] = {
            "current_travel_plan": {
                "destination": "北京", "days": 2,
                "itinerary": {"day_by_day": [{"day": 1, "theme": "探索", "weather": {}, "activities": [], "meals": []}]},
            }
        }
        base_kwargs["user_message"] = "今天有什么安排"
        result = await dispatcher.dispatch(**base_kwargs)
        assert "北京" in result["response"]

    async def test_general_chat_dispatch(self, dispatcher, base_kwargs):
        base_kwargs["intent"] = "general_chat"
        with patch("app.agents.dispatcher.llm_service.chat", new_callable=AsyncMock) as mock_chat:
            mock_chat.return_value = "这是通用的对话回复"
            result = await dispatcher.dispatch(**base_kwargs)
            assert result["response"] == "这是通用的对话回复"

    async def test_travel_plan_extracts_destination_from_message(self, dispatcher, base_kwargs):
        base_kwargs["intent"] = "travel_plan"
        base_kwargs["extracted"] = {}
        base_kwargs["user_message"] = "我想去北京玩3天"
        with patch("app.agents.dispatcher.travel_agent.plan_trip", new_callable=AsyncMock) as mock_plan, \
             patch("app.agents.dispatcher.cross_domain_composer.merge", new_callable=AsyncMock) as mock_merge:
            mock_plan.return_value = type("Result", (), {
                "response": "ok", "travel_plan": {"destination": "北京", "days": 3},
                "to_legacy": lambda self: {"response": self.response, "travel_plan": self.travel_plan},
            })()
            mock_merge.return_value = {"response": "ok", "travel_plan": {"destination": "北京", "days": 3}}
            await dispatcher.dispatch(**base_kwargs)
            # plan_trip should be called with extracted destination and default 3 days
            call_kwargs = mock_plan.call_args.kwargs
            assert call_kwargs["days"] == 3  # extracted from message


class TestLoadRecentMealRecords:
    @pytest.fixture
    def dispatcher(self):
        return AgentDispatcher()

    async def test_load_meal_records(self, dispatcher):
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_record = MagicMock()
        mock_record.date = MagicMock()
        mock_record.meal_type = "breakfast"
        mock_record.foods = [{"name": "鸡蛋", "amount": "2个"}]
        mock_record.total_nutrition = {"calories": 200}
        mock_result.scalars.return_value.all.return_value = [mock_record]
        mock_db.execute = AsyncMock(return_value=mock_result)

        with patch("app.agents.dispatcher.select", return_value=MagicMock()):
            records = await dispatcher._load_recent_meal_records(1, mock_db, limit=10)
            assert len(records) == 1

    async def test_load_meal_dicts(self, dispatcher):
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_record = MagicMock()
        mock_record.date = MagicMock()
        mock_record.meal_type = "lunch"
        mock_record.foods = [{"name": "米饭", "amount": "1碗"}]
        mock_record.total_nutrition = {"calories": 300}
        mock_result.scalars.return_value.all.return_value = [mock_record]
        mock_db.execute = AsyncMock(return_value=mock_result)

        with patch("app.agents.dispatcher.select", return_value=MagicMock()):
            dicts = await dispatcher._load_recent_meal_dicts(1, mock_db, limit=5)
            assert len(dicts) == 1
            assert dicts[0]["meal_type"] == "lunch"
            assert dicts[0]["foods"] == [{"name": "米饭", "amount": "1碗"}]
