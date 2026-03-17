from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, Date, JSON, UniqueConstraint, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=True)
    is_admin = Column(Boolean, default=False, nullable=False, server_default="false")

    # Profile fields
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    age = Column(Integer, nullable=True)
    height_cm = Column(Float, nullable=True)
    gender = Column(String, nullable=True)  # "Male" or "Female"
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationship to weights
    weights = relationship("Weight", back_populates="user", cascade="all, delete-orphan")
    # Workout plans
    workout_plans = relationship("WorkoutPlan", back_populates="user", cascade="all, delete-orphan")


class Weight(Base):
    __tablename__ = "weights"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    weight = Column(Float, nullable=False)
    date = Column(Date, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationship to user
    user = relationship("User", back_populates="weights")


class MetricEntry(Base):
    __tablename__ = "metric_entries"
    __table_args__ = (UniqueConstraint("user_id", "metric_type", "date", name="uq_user_metric_date"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    metric_type = Column(String, nullable=False, index=True)  # "weight", "muscle_index", etc.
    date = Column(Date, nullable=False, index=True)
    value = Column(JSON, nullable=False)  # Flexible payload per metric type
    source = Column(String, nullable=True)  # "device" | "calculated"
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationship to user
    user = relationship("User", backref="metric_entries")


class Exercise(Base):
    __tablename__ = "exercises"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    muscle_group = Column(String, nullable=True)
    equipment = Column(String, nullable=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    owner = relationship("User", backref="custom_exercises")


class WorkoutPlan(Base):
    __tablename__ = "workout_plans"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    duration_value = Column(Integer, nullable=False)
    duration_unit = Column(String, nullable=False)
    start_date = Column(Date, nullable=True)
    is_active = Column(Boolean, default=False, nullable=False, server_default="false")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="workout_plans")
    days = relationship(
        "WorkoutPlanDay",
        back_populates="plan",
        cascade="all, delete-orphan",
        order_by="WorkoutPlanDay.day_number",
    )


class WorkoutPlanDay(Base):
    __tablename__ = "workout_plan_days"
    __table_args__ = (UniqueConstraint("plan_id", "day_number", name="uq_plan_day_number"),)

    id = Column(Integer, primary_key=True, index=True)
    plan_id = Column(Integer, ForeignKey("workout_plans.id", ondelete="CASCADE"), nullable=False, index=True)
    day_number = Column(Integer, nullable=False)
    name = Column(String, nullable=True)
    is_rest_day = Column(Boolean, default=False, nullable=False, server_default="false")
    notes = Column(String, nullable=True)

    plan = relationship("WorkoutPlan", back_populates="days")
    exercises = relationship(
        "WorkoutPlanExercise",
        back_populates="plan_day",
        cascade="all, delete-orphan",
        order_by="WorkoutPlanExercise.order",
    )


class WorkoutPlanExercise(Base):
    __tablename__ = "workout_plan_exercises"

    id = Column(Integer, primary_key=True, index=True)
    plan_day_id = Column(
        Integer, ForeignKey("workout_plan_days.id", ondelete="CASCADE"), nullable=False, index=True
    )
    exercise_id = Column(Integer, ForeignKey("exercises.id"), nullable=False)
    order = Column(Integer, nullable=False, server_default="1")
    sets = Column(Integer, nullable=True)
    reps = Column(Integer, nullable=True)
    weight_kg = Column(Float, nullable=True)
    rest_seconds = Column(Integer, nullable=True)
    notes = Column(String, nullable=True)

    # Per-set override: list of {reps?, weight_kg?} dicts, one per set.
    # When present, len(set_configs) is the effective set count and
    # the top-level `sets`/`reps`/`weight_kg` fields act as defaults/display hints.
    set_configs = Column(JSON, nullable=True)

    plan_day = relationship("WorkoutPlanDay", back_populates="exercises")
    exercise = relationship("Exercise", backref="plan_entries")