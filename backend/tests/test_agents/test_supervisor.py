"""Tests for supervisor agent intent routing."""
import pytest
from unittest.mock import AsyncMock


class TestSupervisor:
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
