from app.services.recommendation import registry


def test_domain_registry_has_stable_order_and_sets():
    assert registry.HOME_DOMAIN == "home"
    assert registry.CATALOG_DOMAIN_ORDER == ("commerce", "restaurant", "travel", "diet")
    assert registry.HOME_FEED_DOMAIN_ORDER == ("travel", "restaurant", "commerce", "diet")
    assert registry.CATALOG_DOMAINS == frozenset(registry.CATALOG_DOMAIN_ORDER)
    assert registry.RECOMMENDATION_DOMAINS == frozenset({registry.HOME_DOMAIN, *registry.CATALOG_DOMAINS})


def test_event_registry_is_consistent():
    assert registry.RECOMMENDATION_EVENTS == frozenset(registry.EVENT_WEIGHTS)
    assert registry.FEEDBACK_EVENTS.issubset(registry.RECOMMENDATION_EVENTS)
    assert registry.POSITIVE_EVENTS.issubset(registry.RECOMMENDATION_EVENTS)
    assert registry.NEGATIVE_EVENTS.issubset(registry.RECOMMENDATION_EVENTS)
    assert registry.CONVERSION_EVENTS.issubset(registry.POSITIVE_EVENTS)
    assert registry.POSITIVE_EVENTS.isdisjoint(registry.NEGATIVE_EVENTS)


def test_event_weight_uses_registry_defaults_and_overrides():
    assert registry.event_weight("click") == 2.0
    assert registry.event_weight("hide") < 0
    assert registry.event_weight("click", override=7) == 7.0


def test_domain_validation_can_exclude_home():
    assert registry.is_valid_domain("home")
    assert not registry.is_valid_domain("home", include_home=False)
    assert registry.is_valid_domain("commerce", include_home=False)
    assert not registry.is_valid_domain("unknown")
