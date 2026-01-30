"""Add profile height (cm) and gender

Revision ID: 003_profile
Revises: 002_profile
Create Date: 2026-01-24

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "003_profile"
down_revision: Union[str, None] = "002_profile"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("height_cm", sa.Float(), nullable=True))
    op.add_column("users", sa.Column("gender", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "gender")
    op.drop_column("users", "height_cm")
