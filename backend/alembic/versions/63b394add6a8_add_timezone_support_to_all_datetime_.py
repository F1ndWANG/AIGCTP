"""add timezone support to all DateTime columns

Revision ID: 63b394add6a8
Revises: a7d9c3b2e6f1
Create Date: 2026-05-09 00:58:33.369378
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '63b394add6a8'
down_revision: Union[str, None] = 'a7d9c3b2e6f1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Map of table -> list of DateTime columns to alter
_TABLES: list[tuple[str, list[str]]] = [
    ("conversations", ["created_at", "updated_at"]),
    ("cached_pois", ["cached_at"]),
    ("categories", ["created_at"]),
    ("products", ["created_at", "updated_at"]),
    ("carts", ["created_at", "updated_at"]),
    ("cart_items", ["created_at"]),
    ("orders", ["created_at", "updated_at"]),
    ("travel_plans", ["created_at", "updated_at"]),
    ("restaurant_recommendations", ["created_at", "updated_at"]),
    ("recommendation_logs", ["created_at"]),
    ("health_profiles", ["created_at", "updated_at"]),
    ("meal_records", ["created_at"]),
    ("diet_plans", ["activated_at", "created_at", "updated_at"]),
    ("task_runs", ["started_at", "finished_at", "created_at", "updated_at"]),
    ("domain_events", ["created_at"]),
    ("users", ["created_at", "updated_at"]),
    ("user_preferences", ["updated_at"]),
]

_ALTER_TEMPLATE = (
    "ALTER TABLE {table} "
    "ALTER COLUMN {column} TYPE TIMESTAMP WITH TIME ZONE "
    "USING {column} AT TIME ZONE 'UTC'"
)


def upgrade() -> None:
    for table, columns in _TABLES:
        for column in columns:
            op.execute(sa.text(_ALTER_TEMPLATE.format(table=table, column=column)))


def downgrade() -> None:
    for table, columns in _TABLES:
        for column in columns:
            op.execute(sa.text(
                f"ALTER TABLE {table} "
                f"ALTER COLUMN {column} TYPE TIMESTAMP WITHOUT TIME ZONE "
                f"USING {column} AT TIME ZONE 'UTC'"
            ))
