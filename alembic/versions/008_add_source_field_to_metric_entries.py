"""Add source field to metric_entries

Revision ID: 008_source_metric_entries
Revises: 007_workout_plans
Create Date: 2026-03-16 08:26:30.840805

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '008_source_metric_entries'
down_revision: Union[str, None] = '007_workout_plans'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('metric_entries', sa.Column('source', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('metric_entries', 'source')
