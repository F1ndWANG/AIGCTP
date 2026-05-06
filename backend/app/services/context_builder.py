"""Helpers for building agent execution context from conversation state."""
from __future__ import annotations

from typing import Any


def has_current_travel_plan(context: dict[str, Any]) -> bool:
    return context.get("current_travel_plan") is not None


def build_preferences(context: dict[str, Any]) -> dict[str, Any]:
    """Merge explicit preferences with learned profile text for prompts."""
    prefs = dict(context.get("user_preferences", {}))
    profile = context.get("user_profile")
    if profile and profile.get("learned"):
        prefs["_profile_text"] = context.get("_profile_text", "")
    return prefs
