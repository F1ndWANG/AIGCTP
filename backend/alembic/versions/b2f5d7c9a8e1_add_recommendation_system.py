"""add recommendation system

Revision ID: b2f5d7c9a8e1
Revises: 305b2b6167ed
Create Date: 2026-05-12 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b2f5d7c9a8e1"
down_revision: Union[str, None] = "305b2b6167ed"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "recommendation_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("domain", sa.String(length=30), nullable=False),
        sa.Column("item_type", sa.String(length=30), nullable=False),
        sa.Column("item_id", sa.String(length=100), nullable=False),
        sa.Column("event_type", sa.String(length=30), nullable=False),
        sa.Column("weight", sa.Float(), nullable=False),
        sa.Column("context", sa.JSON(), nullable=True),
        sa.Column("session_id", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_recommendation_events_id"), "recommendation_events", ["id"], unique=False)
    op.create_index("ix_rec_events_user_domain_time", "recommendation_events", ["user_id", "domain", "created_at"], unique=False)
    op.create_index("ix_rec_events_item", "recommendation_events", ["domain", "item_type", "item_id"], unique=False)
    op.create_index(op.f("ix_recommendation_events_user_id"), "recommendation_events", ["user_id"], unique=False)
    op.create_index(op.f("ix_recommendation_events_domain"), "recommendation_events", ["domain"], unique=False)
    op.create_index(op.f("ix_recommendation_events_item_type"), "recommendation_events", ["item_type"], unique=False)
    op.create_index(op.f("ix_recommendation_events_item_id"), "recommendation_events", ["item_id"], unique=False)
    op.create_index(op.f("ix_recommendation_events_event_type"), "recommendation_events", ["event_type"], unique=False)
    op.create_index(op.f("ix_recommendation_events_session_id"), "recommendation_events", ["session_id"], unique=False)
    op.create_index(op.f("ix_recommendation_events_created_at"), "recommendation_events", ["created_at"], unique=False)

    op.create_table(
        "recommendation_embeddings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("domain", sa.String(length=30), nullable=False),
        sa.Column("item_type", sa.String(length=30), nullable=False),
        sa.Column("item_id", sa.String(length=100), nullable=False),
        sa.Column("text_hash", sa.String(length=64), nullable=False),
        sa.Column("embedding", sa.JSON(), nullable=False),
        sa.Column("model", sa.String(length=100), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_recommendation_embeddings_id"), "recommendation_embeddings", ["id"], unique=False)
    op.create_index("ix_rec_embeddings_item", "recommendation_embeddings", ["domain", "item_type", "item_id"], unique=True)
    op.create_index(op.f("ix_recommendation_embeddings_domain"), "recommendation_embeddings", ["domain"], unique=False)
    op.create_index(op.f("ix_recommendation_embeddings_item_type"), "recommendation_embeddings", ["item_type"], unique=False)
    op.create_index(op.f("ix_recommendation_embeddings_item_id"), "recommendation_embeddings", ["item_id"], unique=False)
    op.create_index(op.f("ix_recommendation_embeddings_text_hash"), "recommendation_embeddings", ["text_hash"], unique=False)

    op.create_table(
        "recommendation_feed_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("domain", sa.String(length=30), nullable=False),
        sa.Column("request_context", sa.JSON(), nullable=True),
        sa.Column("results", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_recommendation_feed_logs_id"), "recommendation_feed_logs", ["id"], unique=False)
    op.create_index("ix_rec_feed_logs_user_domain_time", "recommendation_feed_logs", ["user_id", "domain", "created_at"], unique=False)
    op.create_index(op.f("ix_recommendation_feed_logs_user_id"), "recommendation_feed_logs", ["user_id"], unique=False)
    op.create_index(op.f("ix_recommendation_feed_logs_domain"), "recommendation_feed_logs", ["domain"], unique=False)
    op.create_index(op.f("ix_recommendation_feed_logs_created_at"), "recommendation_feed_logs", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_recommendation_feed_logs_created_at"), table_name="recommendation_feed_logs")
    op.drop_index(op.f("ix_recommendation_feed_logs_domain"), table_name="recommendation_feed_logs")
    op.drop_index(op.f("ix_recommendation_feed_logs_user_id"), table_name="recommendation_feed_logs")
    op.drop_index("ix_rec_feed_logs_user_domain_time", table_name="recommendation_feed_logs")
    op.drop_index(op.f("ix_recommendation_feed_logs_id"), table_name="recommendation_feed_logs")
    op.drop_table("recommendation_feed_logs")

    op.drop_index(op.f("ix_recommendation_embeddings_text_hash"), table_name="recommendation_embeddings")
    op.drop_index(op.f("ix_recommendation_embeddings_item_id"), table_name="recommendation_embeddings")
    op.drop_index(op.f("ix_recommendation_embeddings_item_type"), table_name="recommendation_embeddings")
    op.drop_index(op.f("ix_recommendation_embeddings_domain"), table_name="recommendation_embeddings")
    op.drop_index("ix_rec_embeddings_item", table_name="recommendation_embeddings")
    op.drop_index(op.f("ix_recommendation_embeddings_id"), table_name="recommendation_embeddings")
    op.drop_table("recommendation_embeddings")

    op.drop_index(op.f("ix_recommendation_events_created_at"), table_name="recommendation_events")
    op.drop_index(op.f("ix_recommendation_events_session_id"), table_name="recommendation_events")
    op.drop_index(op.f("ix_recommendation_events_event_type"), table_name="recommendation_events")
    op.drop_index(op.f("ix_recommendation_events_item_id"), table_name="recommendation_events")
    op.drop_index(op.f("ix_recommendation_events_item_type"), table_name="recommendation_events")
    op.drop_index(op.f("ix_recommendation_events_domain"), table_name="recommendation_events")
    op.drop_index(op.f("ix_recommendation_events_user_id"), table_name="recommendation_events")
    op.drop_index("ix_rec_events_item", table_name="recommendation_events")
    op.drop_index("ix_rec_events_user_domain_time", table_name="recommendation_events")
    op.drop_index(op.f("ix_recommendation_events_id"), table_name="recommendation_events")
    op.drop_table("recommendation_events")
