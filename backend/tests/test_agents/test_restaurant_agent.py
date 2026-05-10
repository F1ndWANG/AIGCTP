"""Tests for restaurant_agent — restaurant recommendation and ranking."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


RANKING_RESPONSE = {
    "response": "为您推荐以下餐厅",
    "top_picks": [
        {"name": "全聚德", "reason": "烤鸭名店", "recommended_dishes": ["烤鸭"], "rating_info": "4.8"},
        {"name": "海底捞", "reason": "优质火锅", "recommended_dishes": ["毛肚"], "rating_info": "4.5"},
    ],
}


class TestRecommendRestaurants:
    async def test_empty_results_returns_message(self):
        with patch("app.agents.restaurant_agent.poi_search_restaurants", new_callable=AsyncMock) as mock_search:
            mock_search.return_value = []
            from app.agents.restaurant_agent import recommend_restaurants

            result = await recommend_restaurants(
                city="测试城市", user_message="推荐餐厅", db=AsyncMock(),
            )
            assert "未能找到" in result.response or "没有找到" in result.response

    async def test_recommend_returns_restaurants(self):
        mock_pois = [
            {"poi_id": "R1", "name": "全聚德", "address": "前门大街", "rating": "4.8", "tags": ["烤鸭"]},
            {"poi_id": "R2", "name": "海底捞", "address": "王府井", "rating": "4.5", "tags": ["火锅"]},
        ]
        with patch("app.agents.restaurant_agent.poi_search_restaurants", new_callable=AsyncMock) as mock_search, \
             patch("app.agents.restaurant_agent.llm_service.extract_json", new_callable=AsyncMock) as mock_llm:
            mock_search.return_value = mock_pois
            mock_llm.return_value = RANKING_RESPONSE
            from app.agents.restaurant_agent import recommend_restaurants

            result = await recommend_restaurants(
                city="北京", user_message="推荐北京烤鸭", db=AsyncMock(),
            )
            assert result.response == "为您推荐以下餐厅"
            assert len(result.restaurants) == 2

    async def test_recommend_with_llm_failure_falls_back(self):
        mock_pois = [{"poi_id": "R1", "name": "测试餐厅", "rating": "4.0"}]
        with patch("app.agents.restaurant_agent.poi_search_restaurants", new_callable=AsyncMock) as mock_search, \
             patch("app.agents.restaurant_agent.llm_service.extract_json", new_callable=AsyncMock) as mock_llm:
            mock_search.return_value = mock_pois
            mock_llm.side_effect = Exception("LLM failure")
            from app.agents.restaurant_agent import recommend_restaurants

            result = await recommend_restaurants(
                city="北京", user_message="推荐餐厅", db=AsyncMock(),
            )
            # Should fall back to returning raw search results
            assert len(result.restaurants) > 0
