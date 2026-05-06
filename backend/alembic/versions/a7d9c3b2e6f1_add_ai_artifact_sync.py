"""add ai artifact sync fields

Revision ID: a7d9c3b2e6f1
Revises: 9c1e2f6a4d3b
Create Date: 2026-05-06
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a7d9c3b2e6f1"
down_revision: Union[str, None] = "9c1e2f6a4d3b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("products") as batch_op:
        batch_op.add_column(sa.Column("source", sa.String(length=30), nullable=True))
        batch_op.add_column(sa.Column("source_session_id", sa.String(length=100), nullable=True))
        batch_op.create_index("ix_products_source", ["source"])
        batch_op.create_index("ix_products_source_session_id", ["source_session_id"])

    op.execute("UPDATE products SET source = 'seed' WHERE source IS NULL")

    op.create_table(
        "restaurant_recommendations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.String(length=100), nullable=True),
        sa.Column("city", sa.String(length=100), nullable=True),
        sa.Column("query", sa.String(length=500), nullable=True),
        sa.Column("response", sa.String(length=3000), nullable=True),
        sa.Column("restaurants", sa.JSON(), nullable=True),
        sa.Column("selected_restaurant", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_restaurant_recommendations_user_id", "restaurant_recommendations", ["user_id"])
    op.create_index("ix_restaurant_recommendations_session_id", "restaurant_recommendations", ["session_id"])
    op.create_index(
        "ix_restaurant_recs_user_session",
        "restaurant_recommendations",
        ["user_id", "session_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_restaurant_recs_user_session", table_name="restaurant_recommendations")
    op.drop_index("ix_restaurant_recommendations_session_id", table_name="restaurant_recommendations")
    op.drop_index("ix_restaurant_recommendations_user_id", table_name="restaurant_recommendations")
    op.drop_table("restaurant_recommendations")

    with op.batch_alter_table("products") as batch_op:
        batch_op.drop_index("ix_products_source_session_id")
        batch_op.drop_index("ix_products_source")
        batch_op.drop_column("source_session_id")
        batch_op.drop_column("source")
