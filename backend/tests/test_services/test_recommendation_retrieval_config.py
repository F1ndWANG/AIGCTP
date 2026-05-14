from app.services.recommendation import retrieval


def test_candidate_pool_limit_uses_configured_boundary(monkeypatch):
    monkeypatch.setattr(retrieval.settings, "RECOMMENDATION_MAX_CANDIDATES", 25)

    assert retrieval._candidate_pool_limit(10) == 25
    assert retrieval._candidate_pool_limit(40) == 40


def test_candidate_pool_limit_clamps_extreme_configuration(monkeypatch):
    monkeypatch.setattr(retrieval.settings, "RECOMMENDATION_MAX_CANDIDATES", 5000)

    assert retrieval._candidate_pool_limit(10) == 500

    monkeypatch.setattr(retrieval.settings, "RECOMMENDATION_MAX_CANDIDATES", 0)

    assert retrieval._candidate_pool_limit(10) == 10
