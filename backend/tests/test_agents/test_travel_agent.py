"""Tests for travel agent adjustment helpers."""


def test_replace_all_current_pois_when_user_says_these_spots_were_seen():
    from app.agents.travel_agent import _infer_excluded_pois

    itinerary = {
        "day_by_day": [
            {
                "activities": [
                    {"poi": "故宫博物院"},
                    {"poi": "雍和宫"},
                    {"poi": "天安门"},
                ]
            }
        ]
    }

    excluded = _infer_excluded_pois("这几个景点我都玩过了，换成别的", itinerary)

    assert excluded == ["故宫博物院", "雍和宫", "天安门"]


def test_replace_excluded_activities_removes_stale_pois():
    from app.agents.travel_agent import _replace_excluded_activities

    itinerary = {
        "day_by_day": [
            {
                "activities": [
                    {"time": "上午", "poi": "故宫博物院", "description": "参观故宫博物院"},
                    {"time": "下午", "poi": "雍和宫", "description": "参观雍和宫"},
                    {"time": "晚上", "poi": "天安门", "description": "参观天安门"},
                ]
            }
        ]
    }
    replacement_pois = [
        {"name": "什刹海"},
        {"name": "天坛公园"},
        {"name": "景山公园"},
    ]

    _replace_excluded_activities(
        itinerary,
        replacement_pois,
        ["故宫博物院", "雍和宫", "天安门"],
    )

    activities = itinerary["day_by_day"][0]["activities"]
    assert [activity["poi"] for activity in activities] == ["什刹海", "天坛公园", "景山公园"]
