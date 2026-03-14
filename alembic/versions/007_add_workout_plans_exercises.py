"""Add workout plans, days, exercises

Revision ID: 007_workout_plans
Revises: 006_is_admin
Create Date: 2026-03-13

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "007_workout_plans"
down_revision: Union[str, None] = "006_is_admin"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "exercises",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("muscle_group", sa.String(), nullable=True),
        sa.Column("equipment", sa.String(), nullable=True),
        sa.Column("owner_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_exercises_id"), "exercises", ["id"], unique=False)
    op.create_index(op.f("ix_exercises_owner_id"), "exercises", ["owner_id"], unique=False)

    op.create_table(
        "workout_plans",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("duration_value", sa.Integer(), nullable=False),
        sa.Column("duration_unit", sa.String(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_workout_plans_id"), "workout_plans", ["id"], unique=False)
    op.create_index(op.f("ix_workout_plans_user_id"), "workout_plans", ["user_id"], unique=False)

    op.create_table(
        "workout_plan_days",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("plan_id", sa.Integer(), nullable=False),
        sa.Column("day_number", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("is_rest_day", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("notes", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["plan_id"], ["workout_plans.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("plan_id", "day_number", name="uq_plan_day_number"),
    )
    op.create_index(op.f("ix_workout_plan_days_id"), "workout_plan_days", ["id"], unique=False)
    op.create_index(op.f("ix_workout_plan_days_plan_id"), "workout_plan_days", ["plan_id"], unique=False)

    op.create_table(
        "workout_plan_exercises",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("plan_day_id", sa.Integer(), nullable=False),
        sa.Column("exercise_id", sa.Integer(), nullable=False),
        sa.Column("order", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("sets", sa.Integer(), nullable=True),
        sa.Column("reps", sa.Integer(), nullable=True),
        sa.Column("weight_kg", sa.Float(), nullable=True),
        sa.Column("rest_seconds", sa.Integer(), nullable=True),
        sa.Column("notes", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["exercise_id"], ["exercises.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["plan_day_id"], ["workout_plan_days.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_workout_plan_exercises_id"), "workout_plan_exercises", ["id"], unique=False)
    op.create_index(op.f("ix_workout_plan_exercises_plan_day_id"), "workout_plan_exercises", ["plan_day_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_workout_plan_exercises_plan_day_id"), table_name="workout_plan_exercises")
    op.drop_index(op.f("ix_workout_plan_exercises_id"), table_name="workout_plan_exercises")
    op.drop_table("workout_plan_exercises")
    op.drop_index(op.f("ix_workout_plan_days_plan_id"), table_name="workout_plan_days")
    op.drop_index(op.f("ix_workout_plan_days_id"), table_name="workout_plan_days")
    op.drop_table("workout_plan_days")
    op.drop_index(op.f("ix_workout_plans_user_id"), table_name="workout_plans")
    op.drop_index(op.f("ix_workout_plans_id"), table_name="workout_plans")
    op.drop_table("workout_plans")
    op.drop_index(op.f("ix_exercises_owner_id"), table_name="exercises")
    op.drop_index(op.f("ix_exercises_id"), table_name="exercises")
    op.drop_table("exercises")
