from app.services.recommendation import ranker


def test_configured_score_weights_keep_defaults_for_invalid_json(monkeypatch):
    monkeypatch.setattr(ranker.settings, "RECOMMENDATION_SCORE_WEIGHTS", "{invalid")

    weights = ranker._configured_score_weights()

    assert weights == ranker.DEFAULT_SCORE_WEIGHTS


def test_configured_score_weights_support_runtime_overrides(monkeypatch):
    monkeypatch.setattr(
        ranker.settings,
        "RECOMMENDATION_SCORE_WEIGHTS",
        '{"semantic_score": 2.0, "popularity": 0.0, "unknown": 99}',
    )

    weights = ranker._configured_score_weights()

    assert round(sum(weights.values()), 6) == 1
    assert weights["semantic_score"] > ranker.DEFAULT_SCORE_WEIGHTS["semantic_score"]
    assert weights["popularity"] == 0
    assert "unknown" not in weights


def test_mmr_relevance_weight_is_clamped(monkeypatch):
    monkeypatch.setattr(ranker.settings, "RECOMMENDATION_MMR_RELEVANCE", 3.0)
    assert ranker._mmr_relevance_weight() == 1.0

    monkeypatch.setattr(ranker.settings, "RECOMMENDATION_MMR_RELEVANCE", -1.0)
    assert ranker._mmr_relevance_weight() == 0.0
