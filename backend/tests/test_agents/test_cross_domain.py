"""Tests for cross_domain_composer — post-travel product enrichment."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.agents.cross_domain import CrossDomainComposer


class TestCrossDomainComposer:
    @pytest.fixture
    def composer(self):
        return CrossDomainComposer()

    async def test_merge_no_product_recommendation(self, composer):
        result = {"response": "行程已生成", "travel_plan": {"destination": "北京"}}
        merged = await composer.merge(
            result, destination="北京", extracted={}, user_id=1, db=AsyncMock(), context={}
        )
        assert merged == result  # unchanged

    async def test_merge_with_product_recommendation(self, composer):
        result = {"response": "行程已生成", "travel_plan": {"destination": "上海"}}
        extracted = {"also_recommend_products": True}
        mock_products = [{"id": 1, "name": "防晒霜", "price": "49.00"}]
        with patch("app.agents.cross_domain.commerce_agent.commerce_recommend", new_callable=AsyncMock) as mock_rec:
            mock_rec.return_value = type("Result", (), {
                "response": "推荐防晒霜", "products": mock_products,
                "to_legacy": lambda self: {"response": "推荐防晒霜", "products": mock_products},
            })()
            merged = await composer.merge(
                result, destination="上海", extracted=extracted, user_id=1, db=AsyncMock(), context={}
            )
            assert "products" in merged

    async def test_merge_commerce_exception_is_graceful(self, composer):
        result = {"response": "行程已生成", "travel_plan": {"destination": "广州"}}
        extracted = {"also_recommend_products": True}
        with patch("app.agents.cross_domain.commerce_agent.commerce_recommend", new_callable=AsyncMock) as mock_rec:
            mock_rec.side_effect = Exception("Commerce agent failure")
            merged = await composer.merge(
                result, destination="广州", extracted=extracted, user_id=1, db=AsyncMock(), context={}
            )
            # Should return original result without crashing
            assert merged == result
