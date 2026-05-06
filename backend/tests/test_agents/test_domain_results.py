"""Tests for typed domain agent result contracts."""

from app.agents.domain_results import (
    CartAgentResult,
    CommerceRecommendationResult,
    DietAgentResult,
    ReorderAgentResult,
    RestaurantAgentResult,
    TravelAgentResult,
    TravelPlanArtifact,
    to_legacy_payload,
)
from app.agents.result import AgentResult


def test_travel_agent_result_converts_to_legacy_payload():
    result = TravelAgentResult(
        response="行程已生成",
        travel_plan=TravelPlanArtifact(
            destination="北京",
            days=2,
            itinerary={"day_by_day": []},
            preferences={"pace": "relaxed"},
        ),
    )

    legacy = to_legacy_payload(result)

    assert legacy["response"] == "行程已生成"
    assert legacy["travel_plan"]["destination"] == "北京"
    assert legacy["travel_plan"]["days"] == 2
    assert legacy["travel_plan"]["preferences"]["pace"] == "relaxed"


def test_restaurant_agent_result_converts_to_agent_result():
    typed = RestaurantAgentResult(
        response="推荐这些餐厅",
        restaurants=[{"name": "测试餐厅"}],
        city="成都",
    )

    result = AgentResult.from_legacy(typed)

    assert result.response == "推荐这些餐厅"
    assert result.restaurants == [{"name": "测试餐厅"}]
    assert result.artifacts["city"] == "成都"


def test_diet_agent_result_preserves_plan_and_meal_artifacts():
    typed = DietAgentResult(
        response="饮食建议",
        diet_plan={"title": "减脂计划"},
        meal_record={"id": 1, "foods": [{"name": "鸡蛋"}]},
    )

    legacy = to_legacy_payload(typed)

    assert legacy["response"] == "饮食建议"
    assert legacy["diet_plan"]["title"] == "减脂计划"
    assert legacy["meal_record"]["id"] == 1


def test_commerce_results_preserve_recommendation_cart_and_reorder_fields():
    recommendation = to_legacy_payload(
        CommerceRecommendationResult(
            response="推荐商品",
            products=[{"id": 1, "name": "雨伞"}],
        )
    )
    cart = to_legacy_payload(
        CartAgentResult(
            response="已加购",
            cart_items=[{"id": 2, "quantity": 1}],
        )
    )
    reorder = to_legacy_payload(
        ReorderAgentResult(
            response="已复购",
            order_id=3,
            items_added=2,
        )
    )

    assert recommendation["products"][0]["name"] == "雨伞"
    assert cart["cart_items"][0]["quantity"] == 1
    assert reorder["order_id"] == 3
    assert reorder["items_added"] == 2
