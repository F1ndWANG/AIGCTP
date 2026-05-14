"""align schema with current models

Revision ID: e6a1b9c4d2f0
Revises: 63b394add6a8, d3f8a92b7c11
Create Date: 2026-05-14 12:05:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e6a1b9c4d2f0"
down_revision: Union[str, Sequence[str], None] = ("63b394add6a8", "d3f8a92b7c11")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index("ix_conversations_user_updated", "conversations", ["user_id", "updated_at"], unique=False)
    op.create_index("ix_diet_plans_user_status", "diet_plans", ["user_id", "status"], unique=False)
    op.create_index("ix_products_category_status", "products", ["category_id", "status"], unique=False)
    op.create_index("ix_rec_logs_user_type", "recommendation_logs", ["user_id", "content_type"], unique=False)
    op.create_index("ix_travel_plans_user_status", "travel_plans", ["user_id", "status"], unique=False)

    op.alter_column(
        "orders",
        "total_amount",
        existing_type=sa.Float(),
        type_=sa.Numeric(10, 2),
        existing_nullable=False,
        postgresql_using="total_amount::numeric(10, 2)",
    )
    op.alter_column(
        "products",
        "price",
        existing_type=sa.Float(),
        type_=sa.Numeric(10, 2),
        existing_nullable=False,
        postgresql_using="price::numeric(10, 2)",
    )
    op.alter_column(
        "products",
        "original_price",
        existing_type=sa.Float(),
        type_=sa.Numeric(10, 2),
        existing_nullable=True,
        postgresql_using="original_price::numeric(10, 2)",
    )
    op.alter_column(
        "restaurant_recommendations",
        "response",
        existing_type=sa.String(length=3000),
        type_=sa.String(length=5000),
        existing_nullable=True,
    )

    # Older local databases may have had this implicit index from an earlier model
    # shape. The current schema uses ix_rec_impressions_impression instead.
    op.execute("DROP INDEX IF EXISTS ix_recommendation_impressions_impression_id")


def downgrade() -> None:
    op.create_index(
        "ix_recommendation_impressions_impression_id",
        "recommendation_impressions",
        ["impression_id"],
        unique=False,
    )
    op.alter_column(
        "restaurant_recommendations",
        "response",
        existing_type=sa.String(length=5000),
        type_=sa.String(length=3000),
        existing_nullable=True,
    )
    op.alter_column(
        "products",
        "original_price",
        existing_type=sa.Numeric(10, 2),
        type_=sa.Float(),
        existing_nullable=True,
        postgresql_using="original_price::double precision",
    )
    op.alter_column(
        "products",
        "price",
        existing_type=sa.Numeric(10, 2),
        type_=sa.Float(),
        existing_nullable=False,
        postgresql_using="price::double precision",
    )
    op.alter_column(
        "orders",
        "total_amount",
        existing_type=sa.Numeric(10, 2),
        type_=sa.Float(),
        existing_nullable=False,
        postgresql_using="total_amount::double precision",
    )

    op.drop_index("ix_travel_plans_user_status", table_name="travel_plans")
    op.drop_index("ix_rec_logs_user_type", table_name="recommendation_logs")
    op.drop_index("ix_products_category_status", table_name="products")
    op.drop_index("ix_diet_plans_user_status", table_name="diet_plans")
    op.drop_index("ix_conversations_user_updated", table_name="conversations")
