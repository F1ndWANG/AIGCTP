"""add travel note sharing

Revision ID: c4a9d2e8b7f0
Revises: b2f5d7c9a8e1
Create Date: 2026-05-12 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c4a9d2e8b7f0"
down_revision: Union[str, None] = "b2f5d7c9a8e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "travel_notes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("author_id", sa.Integer(), nullable=False),
        sa.Column("travel_plan_id", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("destination", sa.String(length=100), nullable=True),
        sa.Column("tags", sa.JSON(), nullable=True),
        sa.Column("images", sa.JSON(), nullable=True),
        sa.Column("visibility", sa.String(length=20), nullable=True),
        sa.Column("is_featured", sa.Boolean(), nullable=True),
        sa.Column("view_count", sa.Integer(), nullable=True),
        sa.Column("like_count", sa.Integer(), nullable=True),
        sa.Column("save_count", sa.Integer(), nullable=True),
        sa.Column("comment_count", sa.Integer(), nullable=True),
        sa.Column("share_count", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["travel_plan_id"], ["travel_plans.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_travel_notes_id"), "travel_notes", ["id"], unique=False)
    op.create_index(op.f("ix_travel_notes_author_id"), "travel_notes", ["author_id"], unique=False)
    op.create_index(op.f("ix_travel_notes_travel_plan_id"), "travel_notes", ["travel_plan_id"], unique=False)
    op.create_index(op.f("ix_travel_notes_destination"), "travel_notes", ["destination"], unique=False)
    op.create_index(op.f("ix_travel_notes_visibility"), "travel_notes", ["visibility"], unique=False)
    op.create_index(op.f("ix_travel_notes_created_at"), "travel_notes", ["created_at"], unique=False)
    op.create_index("ix_travel_notes_visibility_destination", "travel_notes", ["visibility", "destination"], unique=False)
    op.create_index("ix_travel_notes_author_created", "travel_notes", ["author_id", "created_at"], unique=False)

    op.create_table(
        "travel_note_interactions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("note_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("interaction_type", sa.String(length=30), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["note_id"], ["travel_notes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("note_id", "user_id", "interaction_type", name="uq_travel_note_interaction"),
    )
    op.create_index(op.f("ix_travel_note_interactions_id"), "travel_note_interactions", ["id"], unique=False)
    op.create_index(op.f("ix_travel_note_interactions_note_id"), "travel_note_interactions", ["note_id"], unique=False)
    op.create_index(op.f("ix_travel_note_interactions_user_id"), "travel_note_interactions", ["user_id"], unique=False)
    op.create_index(op.f("ix_travel_note_interactions_interaction_type"), "travel_note_interactions", ["interaction_type"], unique=False)
    op.create_index("ix_travel_note_interactions_user_type", "travel_note_interactions", ["user_id", "interaction_type"], unique=False)

    op.create_table(
        "travel_note_comments",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("note_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("content", sa.String(length=1000), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["note_id"], ["travel_notes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_travel_note_comments_id"), "travel_note_comments", ["id"], unique=False)
    op.create_index(op.f("ix_travel_note_comments_note_id"), "travel_note_comments", ["note_id"], unique=False)
    op.create_index(op.f("ix_travel_note_comments_user_id"), "travel_note_comments", ["user_id"], unique=False)
    op.create_index(op.f("ix_travel_note_comments_created_at"), "travel_note_comments", ["created_at"], unique=False)
    op.create_index("ix_travel_note_comments_note_created", "travel_note_comments", ["note_id", "created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_travel_note_comments_note_created", table_name="travel_note_comments")
    op.drop_index(op.f("ix_travel_note_comments_created_at"), table_name="travel_note_comments")
    op.drop_index(op.f("ix_travel_note_comments_user_id"), table_name="travel_note_comments")
    op.drop_index(op.f("ix_travel_note_comments_note_id"), table_name="travel_note_comments")
    op.drop_index(op.f("ix_travel_note_comments_id"), table_name="travel_note_comments")
    op.drop_table("travel_note_comments")

    op.drop_index("ix_travel_note_interactions_user_type", table_name="travel_note_interactions")
    op.drop_index(op.f("ix_travel_note_interactions_interaction_type"), table_name="travel_note_interactions")
    op.drop_index(op.f("ix_travel_note_interactions_user_id"), table_name="travel_note_interactions")
    op.drop_index(op.f("ix_travel_note_interactions_note_id"), table_name="travel_note_interactions")
    op.drop_index(op.f("ix_travel_note_interactions_id"), table_name="travel_note_interactions")
    op.drop_table("travel_note_interactions")

    op.drop_index("ix_travel_notes_author_created", table_name="travel_notes")
    op.drop_index("ix_travel_notes_visibility_destination", table_name="travel_notes")
    op.drop_index(op.f("ix_travel_notes_created_at"), table_name="travel_notes")
    op.drop_index(op.f("ix_travel_notes_visibility"), table_name="travel_notes")
    op.drop_index(op.f("ix_travel_notes_destination"), table_name="travel_notes")
    op.drop_index(op.f("ix_travel_notes_travel_plan_id"), table_name="travel_notes")
    op.drop_index(op.f("ix_travel_notes_author_id"), table_name="travel_notes")
    op.drop_index(op.f("ix_travel_notes_id"), table_name="travel_notes")
    op.drop_table("travel_notes")
