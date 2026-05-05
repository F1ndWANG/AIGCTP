"""Tests for diet agent plan fallback behavior."""


def test_weekly_weight_loss_request_builds_fallback_plan():
    from app.agents.diet_agent import _fallback_diet_plan, _wants_diet_plan

    message = "帮我做一周的减肥饮食计划"

    plan = _fallback_diet_plan(message)

    assert _wants_diet_plan(message)
    assert plan["duration_days"] == 7
    assert "减脂" in plan["title"]
    assert len(plan["meals"]["day_by_day"]) == 7
    assert all(len(day["meals"]) == 3 for day in plan["meals"]["day_by_day"])
