"""add_diet_plan_activation

Revision ID: 9c1e2f6a4d3b
Revises: 305b2b6167ed
Create Date: 2026-05-05 23:10:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "9c1e2f6a4d3b"
down_revision: Union[str, None] = "305b2b6167ed"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("diet_plans", sa.Column("activated_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("diet_plans", "activated_at")
