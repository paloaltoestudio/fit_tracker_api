"""009_add_set_configs_to_workout_plan_exercises

Revision ID: 192bb5a2c72e
Revises: 008_source_metric_entries
Create Date: 2026-03-17 13:09:12.605097

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '192bb5a2c72e'
down_revision: Union[str, None] = '008_source_metric_entries'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('workout_plan_exercises', sa.Column('set_configs', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('workout_plan_exercises', 'set_configs')
