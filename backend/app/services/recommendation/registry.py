from __future__ import annotations

from types import MappingProxyType


HOME_DOMAIN = "home"
CATALOG_DOMAIN_ORDER = ("commerce", "restaurant", "travel", "diet")
HOME_FEED_DOMAIN_ORDER = ("travel", "restaurant", "commerce", "diet")
CATALOG_DOMAINS = frozenset(CATALOG_DOMAIN_ORDER)
RECOMMENDATION_DOMAINS = frozenset({HOME_DOMAIN, *CATALOG_DOMAINS})

EVENT_WEIGHTS = MappingProxyType({
    "view": 1.0,
    "click": 2.0,
    "chat_mention": 2.0,
    "save": 3.0,
    "select": 4.0,
    "add_cart": 4.0,
    "confirm_plan": 5.0,
    "order": 6.0,
    "like": 5.0,
    "dislike": -6.0,
    "hide": -5.0,
    "share": 6.0,
    "comment": 4.0,
})
RECOMMENDATION_EVENTS = frozenset(EVENT_WEIGHTS.keys())
FEEDBACK_EVENTS = frozenset({"like", "dislike", "hide", "save", "select"})
NEGATIVE_EVENTS = frozenset({"dislike", "hide"})
POSITIVE_EVENTS = frozenset({"click", "save", "select", "add_cart", "confirm_plan", "order", "like", "share", "comment"})
CONVERSION_EVENTS = frozenset({"save", "select", "add_cart", "confirm_plan", "order", "like", "share", "comment"})


def is_valid_domain(domain: str, *, include_home: bool = True) -> bool:
    domains = RECOMMENDATION_DOMAINS if include_home else CATALOG_DOMAINS
    return domain in domains


def event_weight(event_type: str, override: float | None = None) -> float:
    if override is not None:
        return float(override)
    return EVENT_WEIGHTS[event_type]
