from __future__ import annotations

from typing import Any


def build_candidate_bundle(
    *,
    pois: list[dict[str, Any]],
    restaurants: list[dict[str, Any]],
    hotels: list[dict[str, Any]],
    products: list[dict[str, Any]],
    travel_notes: list[dict[str, Any]] | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """Normalize travel planning candidates for the optimizer."""

    return {
        "pois": pois or [],
        "restaurants": restaurants or [],
        "hotels": hotels or [],
        "products": products or [],
        "travel_notes": travel_notes or [],
    }
