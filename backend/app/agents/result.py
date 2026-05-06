"""Stable result contract for agent orchestration.

Domain agents still return plain dictionaries internally for now. This adapter
centralizes that legacy shape at the orchestration boundary so API code no
longer depends on scattered ad-hoc keys.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.agents.domain_results import to_legacy_payload


_KNOWN_KEYS = {
    "response",
    "travel_plan",
    "products",
    "restaurants",
    "restaurant_recommendation_id",
    "recommendation_id",
    "restaurant_recommendation",
    "diet_plan",
    "cart_items",
    "artifacts",
}


@dataclass(slots=True)
class AgentResult:
    response: str
    travel_plan: dict[str, Any] | None = None
    products: list[Any] = field(default_factory=list)
    restaurants: list[Any] = field(default_factory=list)
    restaurant_recommendation_id: int | None = None
    restaurant_recommendation: Any | None = None
    diet_plan: dict[str, Any] | None = None
    cart_items: list[Any] = field(default_factory=list)
    artifacts: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_legacy(cls, payload: dict[str, Any] | Any) -> "AgentResult":
        """Normalize the historical dict contract returned by domain agents."""
        payload = to_legacy_payload(payload)
        artifacts = dict(payload.get("artifacts") or {})
        for key, value in payload.items():
            if key not in _KNOWN_KEYS:
                artifacts[key] = value

        return cls(
            response=str(payload.get("response") or ""),
            travel_plan=payload.get("travel_plan"),
            products=list(payload.get("products") or []),
            restaurants=list(payload.get("restaurants") or []),
            restaurant_recommendation_id=payload.get("restaurant_recommendation_id") or payload.get("recommendation_id"),
            restaurant_recommendation=payload.get("restaurant_recommendation"),
            diet_plan=payload.get("diet_plan"),
            cart_items=list(payload.get("cart_items") or []),
            artifacts=artifacts,
        )

    def to_legacy(self) -> dict[str, Any]:
        """Return the API-compatible dictionary shape used by existing callers."""
        return {
            "response": self.response,
            "travel_plan": self.travel_plan,
            "products": self.products,
            "restaurants": self.restaurants,
            "restaurant_recommendation_id": self.restaurant_recommendation_id,
            "restaurant_recommendation": self.restaurant_recommendation,
            "diet_plan": self.diet_plan,
            "cart_items": self.cart_items,
            "artifacts": self.artifacts,
        }
