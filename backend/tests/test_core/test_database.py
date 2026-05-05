"""Tests for database initialization."""
import pytest
from app.core.database import Base


class TestDatabase:
    async def test_metadata_has_tables(self):
        """Verify all expected models are registered in Base metadata."""
        table_names = Base.metadata.tables.keys()
        expected = {
            "users", "user_preferences", "travel_plans",
            "conversations", "cached_pois",
            "health_profiles", "meal_records", "diet_plans",
        }
        assert expected.issubset(set(table_names)), f"Missing tables: {expected - set(table_names)}"
