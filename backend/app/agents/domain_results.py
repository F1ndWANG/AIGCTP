"""Typed result objects for domain agents.

These types are the internal contract for domain agents. API compatibility is
kept by converting them to the existing dictionary shape at module boundaries.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


class LegacyConvertible(Protocol):
    def to_legacy(self) -> dict[str, Any]:
        ...


@dataclass(slots=True)
class TravelPlanArtifact:
    destination: str
    days: int
    itinerary: dict[str, Any]
    preferences: dict[str, Any] = field(default_factory=dict)

    def to_legacy(self) -> dict[str, Any]:
        return {
            "destination": self.destination,
            "days": self.days,
            "itinerary": self.itinerary,
            "preferences": self.preferences,
        }


@dataclass(slots=True)
class TravelAgentResult:
    response: str
    travel_plan: TravelPlanArtifact | None = None

    def to_legacy(self) -> dict[str, Any]:
        return {
            "response": self.response,
            "travel_plan": self.travel_plan.to_legacy() if self.travel_plan else None,
        }


@dataclass(slots=True)
class RestaurantAgentResult:
    response: str
    restaurants: list[dict[str, Any]] = field(default_factory=list)
    city: str = ""

    def to_legacy(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "response": self.response,
            "restaurants": self.restaurants,
        }
        if self.city:
            payload["city"] = self.city
        return payload


@dataclass(slots=True)
class DietAgentResult:
    response: str
    diet_plan: dict[str, Any] | None = None
    meal_record: dict[str, Any] | None = None

    def to_legacy(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"response": self.response}
        if self.diet_plan is not None:
            payload["diet_plan"] = self.diet_plan
        if self.meal_record is not None:
            payload["meal_record"] = self.meal_record
        return payload


@dataclass(slots=True)
class CommerceRecommendationResult:
    response: str
    products: list[dict[str, Any]] = field(default_factory=list)

    def to_legacy(self) -> dict[str, Any]:
        return {
            "response": self.response,
            "products": self.products,
        }


@dataclass(slots=True)
class CartAgentResult:
    response: str
    cart_items: list[dict[str, Any]] = field(default_factory=list)

    def to_legacy(self) -> dict[str, Any]:
        return {
            "response": self.response,
            "cart_items": self.cart_items,
        }


@dataclass(slots=True)
class ReorderAgentResult:
    response: str
    order_id: int
    items_added: int

    def to_legacy(self) -> dict[str, Any]:
        return {
            "response": self.response,
            "order_id": self.order_id,
            "items_added": self.items_added,
        }


def to_legacy_payload(payload: dict[str, Any] | LegacyConvertible) -> dict[str, Any]:
    if hasattr(payload, "to_legacy"):
        return payload.to_legacy()
    return payload
