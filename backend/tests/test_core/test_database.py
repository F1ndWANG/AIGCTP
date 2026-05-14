"""Tests for database initialization."""
from app.core.database import Base, should_auto_create_tables
from app.core.config import settings


class TestDatabase:
    async def test_metadata_has_tables(self):
        """Verify all expected models are registered in Base metadata."""
        table_names = Base.metadata.tables.keys()
        expected = {
            "users", "user_preferences", "travel_plans",
            "conversations", "cached_pois",
            "health_profiles", "meal_records", "diet_plans",
            "task_runs", "domain_events",
        }
        assert expected.issubset(set(table_names)), f"Missing tables: {expected - set(table_names)}"

    async def test_auto_create_tables_defaults_to_dev_only(self, monkeypatch):
        monkeypatch.setattr(settings, "DB_AUTO_CREATE_TABLES", None)
        monkeypatch.setattr(settings, "APP_ENV", "development")
        assert should_auto_create_tables() is True

        monkeypatch.setattr(settings, "APP_ENV", "production")
        assert should_auto_create_tables() is False

    async def test_auto_create_tables_explicit_override(self, monkeypatch):
        monkeypatch.setattr(settings, "APP_ENV", "production")
        monkeypatch.setattr(settings, "DB_AUTO_CREATE_TABLES", True)
        assert should_auto_create_tables() is True

        monkeypatch.setattr(settings, "DB_AUTO_CREATE_TABLES", False)
        assert should_auto_create_tables() is False
