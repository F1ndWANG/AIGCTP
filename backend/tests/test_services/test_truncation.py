"""Tests for conversation truncation service."""
from app.services.truncation import _estimate_tokens, truncate_messages


class TestEstimateTokens:
    async def test_estimate_tokens_empty(self):
        assert _estimate_tokens("") == 0

    async def test_estimate_tokens_english(self):
        text = "hello world " * 10
        assert _estimate_tokens(text) > 0

    async def test_estimate_tokens_mixed(self):
        text = "你好 world 测试 " * 5
        assert _estimate_tokens(text) > 0


class TestTruncate:
    async def test_truncate_below_soft(self):
        msgs = [{"role": "user", "content": "hello"}] * 3
        result = await truncate_messages(msgs)
        assert len(result) == 3

    async def test_truncate_very_long(self):
        long_content = "hello " * 2000
        msgs = [{"role": "user", "content": long_content}]
        result = await truncate_messages(msgs)
        assert len(result) > 0  # should still return messages
