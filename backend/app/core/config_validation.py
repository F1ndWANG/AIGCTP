"""Runtime settings validation rules.

This module intentionally has no dependency on the concrete ``Settings`` class
so validation can be exercised with test doubles and without reloading config.
"""

from __future__ import annotations

import sys
import warnings
from typing import Protocol


class RuntimeSettings(Protocol):
    APP_ENV: str
    DEBUG: bool
    DATABASE_URL: str
    JWT_SECRET: str
    COOKIE_SECURE: bool
    LLM_API_KEY: str | None
    AMAP_API_KEY: str | None
    QWEATHER_API_KEY: str | None
    DB_AUTO_CREATE_TABLES: bool | None
    RECOMMENDATION_MAX_CANDIDATES: int

    @property
    def cors_origins_list(self) -> list[str]: ...

    @property
    def is_production(self) -> bool: ...


DEFAULT_SECRETS = ("dev-secret-change-in-production", "your_jwt_secret_key", "")


def _is_placeholder(value: str | None, markers: tuple[str, ...]) -> bool:
    if not value:
        return True
    normalized = value.lower()
    return any(marker in normalized for marker in markers)


def validate_runtime_settings(current: RuntimeSettings) -> list[str]:
    """Return production-blocking configuration problems."""
    errors = []

    if current.JWT_SECRET in DEFAULT_SECRETS:
        errors.append("JWT_SECRET is set to a default/example value")
    if len(current.JWT_SECRET) < 32:
        errors.append("JWT_SECRET must be at least 32 characters")

    if current.DATABASE_URL.startswith("sqlite"):
        errors.append("DATABASE_URL must not use SQLite in production")

    if current.DB_AUTO_CREATE_TABLES is True:
        errors.append("DB_AUTO_CREATE_TABLES must not be True in production")

    if current.RECOMMENDATION_MAX_CANDIDATES < 1 or current.RECOMMENDATION_MAX_CANDIDATES > 500:
        errors.append("RECOMMENDATION_MAX_CANDIDATES must be between 1 and 500")

    if current.DEBUG:
        errors.append("DEBUG must be False in production")

    if not current.COOKIE_SECURE:
        errors.append("COOKIE_SECURE must be True in production")

    if "*" in current.cors_origins_list:
        errors.append("CORS_ORIGINS must not contain '*' in production")

    if _is_placeholder(current.LLM_API_KEY, ("placeholder", "sk-your-", "replace-with")):
        errors.append("LLM_API_KEY is not set or appears to be a placeholder value")

    if _is_placeholder(current.AMAP_API_KEY, ("your_", "placeholder")):
        errors.append("AMAP_API_KEY is not set or appears to be a placeholder value")

    if _is_placeholder(current.QWEATHER_API_KEY, ("your_", "placeholder")):
        errors.append("QWEATHER_API_KEY is not set or appears to be a placeholder value")

    return errors


def enforce_production_settings(current: RuntimeSettings) -> None:
    """Refuse to start in production mode with unsafe settings."""
    errors = validate_runtime_settings(current)
    if not errors:
        return

    msg = "Production startup failed:\n" + "\n".join(f"  - {error}" for error in errors)
    print(msg, file=sys.stderr)
    sys.exit(1)


def warn_development_settings(current: RuntimeSettings) -> None:
    """Warn about missing or default critical env vars at startup."""
    issues = []
    if not current.LLM_API_KEY:
        issues.append("LLM_API_KEY is not set")
    if current.JWT_SECRET in DEFAULT_SECRETS:
        issues.append("JWT_SECRET is using default value (insecure for production)")
    if issues:
        warnings.warn("Startup environment issues: " + "; ".join(issues), stacklevel=2)
