import pytest

from app.core.config import Settings, validate_runtime_settings
from app.core import config_validation


def _production_settings(**overrides):
    base = {
        "APP_ENV": "production",
        "DEBUG": False,
        "DATABASE_URL": "postgresql+asyncpg://app:pass@db:5432/aigctp",
        "JWT_SECRET": "x" * 40,
        "LLM_API_KEY": "ok",
        "AMAP_API_KEY": "ok",
        "QWEATHER_API_KEY": "ok",
        "COOKIE_SECURE": True,
        "CORS_ORIGINS": "https://example.com",
    }
    base.update(overrides)
    return Settings(**base)


def test_production_validation_rejects_sqlite_and_insecure_cookie():
    errors = validate_runtime_settings(
        _production_settings(
            DATABASE_URL="sqlite+aiosqlite:///prod.db",
            COOKIE_SECURE=False,
        )
    )

    assert "DATABASE_URL must not use SQLite in production" in errors
    assert "COOKIE_SECURE must be True in production" in errors


def test_production_validation_rejects_auto_create_tables():
    errors = validate_runtime_settings(_production_settings(DB_AUTO_CREATE_TABLES=True))

    assert "DB_AUTO_CREATE_TABLES must not be True in production" in errors


def test_production_validation_rejects_unbounded_recommendation_candidates():
    errors = validate_runtime_settings(_production_settings(RECOMMENDATION_MAX_CANDIDATES=2000))

    assert "RECOMMENDATION_MAX_CANDIDATES must be between 1 and 500" in errors


def test_production_validation_rejects_wildcard_cors():
    errors = validate_runtime_settings(_production_settings(CORS_ORIGINS="https://example.com,*"))

    assert "CORS_ORIGINS must not contain '*' in production" in errors


def test_production_validation_accepts_hardened_settings():
    assert validate_runtime_settings(_production_settings()) == []


def test_config_module_reexports_validation_function():
    assert validate_runtime_settings is config_validation.validate_runtime_settings


def test_development_warning_reports_missing_critical_values():
    dev = Settings(
        APP_ENV="development",
        LLM_API_KEY=None,
        JWT_SECRET="dev-secret-change-in-production",
    )

    with pytest.warns(UserWarning, match="LLM_API_KEY is not set"):
        config_validation.warn_development_settings(dev)


def test_enforce_production_settings_exits_for_unsafe_settings(capsys):
    unsafe = _production_settings(JWT_SECRET="short")

    with pytest.raises(SystemExit):
        config_validation.enforce_production_settings(unsafe)

    captured = capsys.readouterr()
    assert "Production startup failed" in captured.err
    assert "JWT_SECRET must be at least 32 characters" in captured.err
