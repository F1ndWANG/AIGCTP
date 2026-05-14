import pytest

from app.models.travel import TravelPlan
from app.services.travel_plan_service import (
    TravelPlanNotFoundError,
    confirm_user_travel_plan,
    delete_user_travel_plan,
    get_user_travel_plan,
    list_user_travel_plans,
)


@pytest.fixture
async def sample_travel_plan(session, test_user):
    plan = TravelPlan(
        user_id=test_user.id,
        destination="西安",
        days=1,
        budget=300,
        preferences={"theme": "古城美食"},
        itinerary={"day_by_day": []},
        status="draft",
    )
    session.add(plan)
    await session.commit()
    await session.refresh(plan)
    return plan


@pytest.mark.anyio
async def test_list_and_get_user_travel_plan(session, test_user, sample_travel_plan):
    plans = await list_user_travel_plans(session, user_id=test_user.id)

    assert [plan.id for plan in plans] == [sample_travel_plan.id]

    found = await get_user_travel_plan(session, user_id=test_user.id, plan_id=sample_travel_plan.id)
    assert found.destination == "西安"


@pytest.mark.anyio
async def test_get_user_travel_plan_rejects_missing_or_other_user(session, sample_travel_plan):
    with pytest.raises(TravelPlanNotFoundError):
        await get_user_travel_plan(session, user_id=999, plan_id=sample_travel_plan.id)


@pytest.mark.anyio
async def test_confirm_user_travel_plan_tracks_and_confirms(session, test_user, sample_travel_plan):
    confirmed = await confirm_user_travel_plan(session, user_id=test_user.id, plan_id=sample_travel_plan.id)

    assert confirmed.status == "confirmed"


@pytest.mark.anyio
async def test_delete_user_travel_plan_removes_plan(session, test_user, sample_travel_plan):
    await delete_user_travel_plan(session, user_id=test_user.id, plan_id=sample_travel_plan.id)

    with pytest.raises(TravelPlanNotFoundError):
        await get_user_travel_plan(session, user_id=test_user.id, plan_id=sample_travel_plan.id)
