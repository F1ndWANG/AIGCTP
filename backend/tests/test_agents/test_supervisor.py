"""Tests for supervisor agent intent routing."""
from unittest.mock import AsyncMock


class TestSupervisor:
    def test_seen_spots_request_routes_to_travel_adjust(self):
        """User asks to replace visited spots should adjust the current plan."""
        from app.agents.supervisor import _classify_intent

        intent, _ = _classify_intent("这几个景点我都玩过了，换成别的", has_travel_plan=True)

        assert intent == "travel_adjust"

    def test_replace_spots_without_plan_stays_non_adjust(self):
        """Replacement wording needs a current plan to become plan adjustment."""
        from app.agents.supervisor import _classify_intent

        intent, _ = _classify_intent("这几个景点我都玩过了，换成别的", has_travel_plan=False)

        assert intent != "travel_adjust"

    async def test_general_chat_intent(self):
        """Verify general_chat returns a response string."""
        from app.agents.supervisor import run_agent
        mock_db = AsyncMock()
        result = await run_agent(
            user_message="你好",
            messages=[{"role": "user", "content": "你好"}],
            context={},
            user_id=1,
            db=mock_db,
        )
        assert "response" in result
        assert isinstance(result["response"], str)
