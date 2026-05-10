"""Tests for travel agent adjustment helpers."""


def test_infer_excluded_pois_all_current_spots():
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


def test_strip_excluded_activities_removes_stale_pois():
    from app.agents.travel_agent import _strip_excluded_activities

    itinerary = {
        "day_by_day": [
            {
                "activities": [
                    {"time": "上午", "poi": "故宫博物院", "description": "参观故宫博物院"},
                    {"time": "下午", "poi": "雍和宫", "description": "参观雍和宫"},
                    {"time": "晚上", "poi": "什刹海", "description": "参观什刹海"},
                ]
            }
        ]
    }

    _strip_excluded_activities(itinerary, ["故宫博物院", "雍和宫"])

    activities = itinerary["day_by_day"][0]["activities"]
    assert [a["poi"] for a in activities] == ["什刹海"]


def test_normalize_poi_name_removes_punctuation():
    from app.agents.travel_agent import _normalize_poi_name
    assert _normalize_poi_name("故宫·博物院") == "故宫博物院"


def test_poi_aliases_strips_suffix():
    from app.agents.travel_agent import _poi_aliases
    aliases = _poi_aliases("天安门广场")
    assert "天安门广场" in aliases
    assert "天安门" in aliases


def test_infer_excluded_pois_matches_related_tiananmen_spots():
    from app.agents.travel_agent import _infer_excluded_pois

    itinerary = {
        "day_by_day": [
            {
                "activities": [
                    {"poi": "天安门广场"},
                    {"poi": "天安门城楼"},
                    {"poi": "故宫博物院"},
                ]
            }
        ]
    }

    excluded = _infer_excluded_pois("我不想去天安门，帮我换别的", itinerary)

    assert "天安门广场" in excluded
    assert "天安门城楼" in excluded
    assert "故宫博物院" not in excluded


def test_dedupe_pois_removes_related_tiananmen_duplicates():
    from app.agents.travel_agent import _dedupe_pois

    pois = [
        {"name": "天安门广场"},
        {"name": "天安门"},
        {"name": "故宫博物院"},
    ]

    deduped = _dedupe_pois(pois)

    assert [poi["name"] for poi in deduped] == ["天安门广场", "故宫博物院"]
