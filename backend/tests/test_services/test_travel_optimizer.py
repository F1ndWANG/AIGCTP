from app.services.travel.optimizer import optimize_itinerary


def test_optimizer_avoids_excluded_pois_and_keeps_required_first():
    itinerary = optimize_itinerary(
        destination="北京",
        days=1,
        pois=[
            {"name": "天坛公园", "rating": 4.8},
            {"name": "故宫博物院", "rating": 4.9},
            {"name": "前门大街", "rating": 4.7},
        ],
        restaurants=[{"name": "护国寺小吃", "category": "本地特色", "rating": 4.6}],
        hotels=[{"name": "前门地铁酒店", "rating": 4.5}],
        products=[{"id": 1, "name": "便携水杯", "price": 69, "tags": ["旅行"]}],
        original_message="北京一日游，必须去天坛，不要去故宫，预算300以内",
        requested_pois=["天坛"],
        avoid_pois=["故宫"],
    )

    activities = itinerary["day_by_day"][0]["activities"]
    names = [item["poi"] for item in activities]
    assert names[0] == "天坛公园"
    assert all("故宫" not in name for name in names)
    assert itinerary["budget_estimate"]["total"] == "约 ¥205/人"
    assert itinerary["optimization"]["algorithm"] == "constraint_heuristic_v1"
