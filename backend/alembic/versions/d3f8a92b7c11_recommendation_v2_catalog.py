"""recommendation v2 catalog and impressions

Revision ID: d3f8a92b7c11
Revises: c4a9d2e8b7f0
Create Date: 2026-05-13 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d3f8a92b7c11"
down_revision: Union[str, None] = "c4a9d2e8b7f0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("recommendation_events", sa.Column("impression_id", sa.String(length=64), nullable=True))
    op.create_index(op.f("ix_recommendation_events_impression_id"), "recommendation_events", ["impression_id"], unique=False)

    op.create_table(
        "recommendation_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("domain", sa.String(length=30), nullable=False),
        sa.Column("item_type", sa.String(length=30), nullable=False),
        sa.Column("source_id", sa.String(length=100), nullable=False),
        sa.Column("source_user_id", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("tags", sa.JSON(), nullable=True),
        sa.Column("city", sa.String(length=100), nullable=True),
        sa.Column("category", sa.String(length=100), nullable=True),
        sa.Column("price", sa.Float(), nullable=True),
        sa.Column("rating", sa.Float(), nullable=True),
        sa.Column("popularity_score", sa.Float(), nullable=False),
        sa.Column("freshness_score", sa.Float(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("image_url", sa.String(length=500), nullable=True),
        sa.Column("url", sa.String(length=500), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["source_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_recommendation_items_id"), "recommendation_items", ["id"], unique=False)
    op.create_index(op.f("ix_recommendation_items_domain"), "recommendation_items", ["domain"], unique=False)
    op.create_index(op.f("ix_recommendation_items_item_type"), "recommendation_items", ["item_type"], unique=False)
    op.create_index(op.f("ix_recommendation_items_source_id"), "recommendation_items", ["source_id"], unique=False)
    op.create_index(op.f("ix_recommendation_items_source_user_id"), "recommendation_items", ["source_user_id"], unique=False)
    op.create_index(op.f("ix_recommendation_items_city"), "recommendation_items", ["city"], unique=False)
    op.create_index(op.f("ix_recommendation_items_category"), "recommendation_items", ["category"], unique=False)
    op.create_index(op.f("ix_recommendation_items_active"), "recommendation_items", ["active"], unique=False)
    op.create_index("ix_rec_items_source", "recommendation_items", ["domain", "item_type", "source_id"], unique=True)
    op.create_index("ix_rec_items_domain_active", "recommendation_items", ["domain", "active"], unique=False)
    op.create_index("ix_rec_items_city_category", "recommendation_items", ["city", "category"], unique=False)
    op.create_index("ix_rec_items_owner", "recommendation_items", ["source_user_id"], unique=False)

    op.create_table(
        "recommendation_impressions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("impression_id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("domain", sa.String(length=30), nullable=False),
        sa.Column("item_type", sa.String(length=30), nullable=False),
        sa.Column("item_id", sa.String(length=100), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("algorithm", sa.String(length=100), nullable=False),
        sa.Column("context", sa.JSON(), nullable=True),
        sa.Column("session_id", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_recommendation_impressions_id"), "recommendation_impressions", ["id"], unique=False)
    op.create_index(op.f("ix_recommendation_impressions_user_id"), "recommendation_impressions", ["user_id"], unique=False)
    op.create_index(op.f("ix_recommendation_impressions_domain"), "recommendation_impressions", ["domain"], unique=False)
    op.create_index(op.f("ix_recommendation_impressions_item_type"), "recommendation_impressions", ["item_type"], unique=False)
    op.create_index(op.f("ix_recommendation_impressions_item_id"), "recommendation_impressions", ["item_id"], unique=False)
    op.create_index(op.f("ix_recommendation_impressions_algorithm"), "recommendation_impressions", ["algorithm"], unique=False)
    op.create_index(op.f("ix_recommendation_impressions_session_id"), "recommendation_impressions", ["session_id"], unique=False)
    op.create_index(op.f("ix_recommendation_impressions_created_at"), "recommendation_impressions", ["created_at"], unique=False)
    op.create_index("ix_rec_impressions_user_domain_time", "recommendation_impressions", ["user_id", "domain", "created_at"], unique=False)
    op.create_index("ix_rec_impressions_item", "recommendation_impressions", ["domain", "item_type", "item_id"], unique=False)
    op.create_index("ix_rec_impressions_impression", "recommendation_impressions", ["impression_id"], unique=True)

    op.create_table(
        "recommendation_feature_snapshots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("domain", sa.String(length=30), nullable=False),
        sa.Column("item_type", sa.String(length=30), nullable=False),
        sa.Column("item_id", sa.String(length=100), nullable=False),
        sa.Column("event_counts", sa.JSON(), nullable=False),
        sa.Column("features", sa.JSON(), nullable=False),
        sa.Column("impressions", sa.Integer(), nullable=False),
        sa.Column("clicks", sa.Integer(), nullable=False),
        sa.Column("conversions", sa.Integer(), nullable=False),
        sa.Column("social_score", sa.Float(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_recommendation_feature_snapshots_id"), "recommendation_feature_snapshots", ["id"], unique=False)
    op.create_index(op.f("ix_recommendation_feature_snapshots_domain"), "recommendation_feature_snapshots", ["domain"], unique=False)
    op.create_index(op.f("ix_recommendation_feature_snapshots_item_type"), "recommendation_feature_snapshots", ["item_type"], unique=False)
    op.create_index(op.f("ix_recommendation_feature_snapshots_item_id"), "recommendation_feature_snapshots", ["item_id"], unique=False)
    op.create_index("ix_rec_feature_item", "recommendation_feature_snapshots", ["domain", "item_type", "item_id"], unique=True)
    op.create_index("ix_rec_feature_domain", "recommendation_feature_snapshots", ["domain", "updated_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_rec_feature_domain", table_name="recommendation_feature_snapshots")
    op.drop_index("ix_rec_feature_item", table_name="recommendation_feature_snapshots")
    op.drop_index(op.f("ix_recommendation_feature_snapshots_item_id"), table_name="recommendation_feature_snapshots")
    op.drop_index(op.f("ix_recommendation_feature_snapshots_item_type"), table_name="recommendation_feature_snapshots")
    op.drop_index(op.f("ix_recommendation_feature_snapshots_domain"), table_name="recommendation_feature_snapshots")
    op.drop_index(op.f("ix_recommendation_feature_snapshots_id"), table_name="recommendation_feature_snapshots")
    op.drop_table("recommendation_feature_snapshots")

    op.drop_index("ix_rec_impressions_impression", table_name="recommendation_impressions")
    op.drop_index("ix_rec_impressions_item", table_name="recommendation_impressions")
    op.drop_index("ix_rec_impressions_user_domain_time", table_name="recommendation_impressions")
    op.drop_index(op.f("ix_recommendation_impressions_created_at"), table_name="recommendation_impressions")
    op.drop_index(op.f("ix_recommendation_impressions_session_id"), table_name="recommendation_impressions")
    op.drop_index(op.f("ix_recommendation_impressions_algorithm"), table_name="recommendation_impressions")
    op.drop_index(op.f("ix_recommendation_impressions_item_id"), table_name="recommendation_impressions")
    op.drop_index(op.f("ix_recommendation_impressions_item_type"), table_name="recommendation_impressions")
    op.drop_index(op.f("ix_recommendation_impressions_domain"), table_name="recommendation_impressions")
    op.drop_index(op.f("ix_recommendation_impressions_user_id"), table_name="recommendation_impressions")
    op.drop_index(op.f("ix_recommendation_impressions_id"), table_name="recommendation_impressions")
    op.drop_table("recommendation_impressions")

    op.drop_index("ix_rec_items_owner", table_name="recommendation_items")
    op.drop_index("ix_rec_items_city_category", table_name="recommendation_items")
    op.drop_index("ix_rec_items_domain_active", table_name="recommendation_items")
    op.drop_index("ix_rec_items_source", table_name="recommendation_items")
    op.drop_index(op.f("ix_recommendation_items_active"), table_name="recommendation_items")
    op.drop_index(op.f("ix_recommendation_items_category"), table_name="recommendation_items")
    op.drop_index(op.f("ix_recommendation_items_city"), table_name="recommendation_items")
    op.drop_index(op.f("ix_recommendation_items_source_user_id"), table_name="recommendation_items")
    op.drop_index(op.f("ix_recommendation_items_source_id"), table_name="recommendation_items")
    op.drop_index(op.f("ix_recommendation_items_item_type"), table_name="recommendation_items")
    op.drop_index(op.f("ix_recommendation_items_domain"), table_name="recommendation_items")
    op.drop_index(op.f("ix_recommendation_items_id"), table_name="recommendation_items")
    op.drop_table("recommendation_items")

    op.drop_index(op.f("ix_recommendation_events_impression_id"), table_name="recommendation_events")
    op.drop_column("recommendation_events", "impression_id")
