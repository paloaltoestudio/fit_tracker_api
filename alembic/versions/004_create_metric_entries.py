"""Create metric_entries table for flexible metrics (weight, muscle_index, etc.)

Revision ID: 004_metrics
Revises: 003_profile
Create Date: 2026-01-24

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "004_metrics"
down_revision: Union[str, None] = "003_profile"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "metric_entries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("metric_type", sa.String(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("value", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "metric_type", "date", name="uq_user_metric_date"),
    )
    op.create_index(op.f("ix_metric_entries_id"), "metric_entries", ["id"], unique=False)
    op.create_index(op.f("ix_metric_entries_user_id"), "metric_entries", ["user_id"], unique=False)
    op.create_index(op.f("ix_metric_entries_metric_type"), "metric_entries", ["metric_type"], unique=False)
    op.create_index(op.f("ix_metric_entries_date"), "metric_entries", ["date"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_metric_entries_date"), table_name="metric_entries")
    op.drop_index(op.f("ix_metric_entries_metric_type"), table_name="metric_entries")
    op.drop_index(op.f("ix_metric_entries_user_id"), table_name="metric_entries")
    op.drop_index(op.f("ix_metric_entries_id"), table_name="metric_entries")
    op.drop_table("metric_entries")
