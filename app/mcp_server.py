"""MCP server for Fit Tracker API.

Exposes all fitness data operations as MCP tools for AI agents (n8n, embedded agents, etc.).
Transport: Streamable HTTP (MCP spec 2025). Mounted at /mcp in the main FastAPI app.

Required env var:
  MCP_API_KEY — Bearer token agents must send in Authorization header (or X-API-Key header)

Every tool accepts a `username` parameter so the agent can operate on any user's data.
"""
import json
from contextlib import contextmanager
from datetime import date as date_type, datetime
from typing import Optional

from mcp.server.fastmcp import FastMCP
from sqlalchemy import func

from app.database import SessionLocal
from app.models import (
    Exercise,
    Goal,
    MetricEntry,
    User,
    Weight,
    WorkoutPlan,
    WorkoutPlanDay,
    WorkoutPlanExercise,
)

mcp = FastMCP(
    "Fit Tracker",
    transport_security={"enable_dns_rebinding_protection": False},
)


@contextmanager
def _db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _user(db, username: str) -> User:
    u = db.query(User).filter(User.username == username).first()
    if not u:
        raise RuntimeError(f"User '{username}' not found.")
    return u


# ─── Profile ─────────────────────────────────────────────────────────────────

@mcp.tool()
def get_profile(username: str) -> dict:
    """Get a user's fitness profile (name, age, height, gender, email)."""
    with _db() as db:
        u = _user(db, username)
        return {
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "first_name": u.first_name,
            "last_name": u.last_name,
            "age": u.age,
            "height_cm": u.height_cm,
            "gender": u.gender,
        }


@mcp.tool()
def update_profile(
    username: str,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    age: Optional[int] = None,
    height_cm: Optional[float] = None,
    gender: Optional[str] = None,
    email: Optional[str] = None,
) -> dict:
    """Update a user's profile. Only provided fields are changed. gender must be 'Male' or 'Female'."""
    with _db() as db:
        u = _user(db, username)
        if first_name is not None:
            u.first_name = first_name
        if last_name is not None:
            u.last_name = last_name
        if age is not None:
            u.age = age
        if height_cm is not None:
            u.height_cm = height_cm
        if gender is not None:
            u.gender = gender
        if email is not None:
            conflict = db.query(User).filter(User.email == email, User.id != u.id).first()
            if conflict:
                raise ValueError("Email already in use.")
            u.email = email
        db.commit()
        db.refresh(u)
        return {
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "first_name": u.first_name,
            "last_name": u.last_name,
            "age": u.age,
            "height_cm": u.height_cm,
            "gender": u.gender,
        }


# ─── Weights ──────────────────────────────────────────────────────────────────

@mcp.tool()
def list_weights(username: str) -> list:
    """List all weight entries for a user, ordered newest first."""
    with _db() as db:
        u = _user(db, username)
        rows = db.query(Weight).filter(Weight.user_id == u.id).order_by(Weight.date.desc()).all()
        return [
            {"id": w.id, "weight": w.weight, "date": w.date.isoformat(), "created_at": w.created_at.isoformat()}
            for w in rows
        ]


@mcp.tool()
def create_weight(username: str, date: str, weight: float) -> dict:
    """Add a weight entry for a user. date: YYYY-MM-DD. weight: kg. One entry per day enforced."""
    with _db() as db:
        u = _user(db, username)
        try:
            d = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            raise ValueError("Invalid date format. Use YYYY-MM-DD.")
        existing = db.query(Weight).filter(Weight.user_id == u.id, Weight.date == d).first()
        if existing:
            raise ValueError(f"Weight entry already exists for {date}. Use update_weight with id={existing.id}.")
        w = Weight(user_id=u.id, weight=weight, date=d)
        db.add(w)
        db.commit()
        db.refresh(w)
        return {"id": w.id, "weight": w.weight, "date": w.date.isoformat(), "created_at": w.created_at.isoformat()}


@mcp.tool()
def update_weight(username: str, weight_id: int, date: Optional[str] = None, weight: Optional[float] = None) -> dict:
    """Update a weight entry by id. Provide date (YYYY-MM-DD) and/or weight (kg)."""
    with _db() as db:
        u = _user(db, username)
        w = db.query(Weight).filter(Weight.id == weight_id, Weight.user_id == u.id).first()
        if not w:
            raise ValueError(f"Weight entry {weight_id} not found.")
        if date is not None:
            try:
                new_date = datetime.strptime(date, "%Y-%m-%d").date()
            except ValueError:
                raise ValueError("Invalid date format. Use YYYY-MM-DD.")
            if new_date != w.date:
                conflict = db.query(Weight).filter(
                    Weight.user_id == u.id, Weight.date == new_date, Weight.id != weight_id
                ).first()
                if conflict:
                    raise ValueError(f"Weight entry already exists for {date}.")
            w.date = new_date
        if weight is not None:
            w.weight = weight
        db.commit()
        db.refresh(w)
        return {"id": w.id, "weight": w.weight, "date": w.date.isoformat(), "created_at": w.created_at.isoformat()}


@mcp.tool()
def delete_weight(username: str, weight_id: int) -> dict:
    """Delete a weight entry by id."""
    with _db() as db:
        u = _user(db, username)
        w = db.query(Weight).filter(Weight.id == weight_id, Weight.user_id == u.id).first()
        if not w:
            raise ValueError(f"Weight entry {weight_id} not found.")
        db.delete(w)
        db.commit()
        return {"message": f"Weight entry {weight_id} deleted."}


# ─── Metrics ──────────────────────────────────────────────────────────────────

@mcp.tool()
def list_metrics(
    username: str,
    metric_type: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> list:
    """List metric entries for a user. Filter by metric_type ('weight'|'muscle_index'|'body_measurements') and/or date range (YYYY-MM-DD)."""
    with _db() as db:
        u = _user(db, username)
        q = db.query(MetricEntry).filter(MetricEntry.user_id == u.id)
        if metric_type:
            q = q.filter(MetricEntry.metric_type == metric_type)
        if date_from:
            q = q.filter(MetricEntry.date >= datetime.strptime(date_from, "%Y-%m-%d").date())
        if date_to:
            q = q.filter(MetricEntry.date <= datetime.strptime(date_to, "%Y-%m-%d").date())
        return [
            {
                "id": e.id,
                "metric_type": e.metric_type,
                "date": e.date.isoformat(),
                "value": e.value,
                "source": e.source,
                "created_at": e.created_at.isoformat(),
            }
            for e in q.order_by(MetricEntry.date.desc()).all()
        ]


@mcp.tool()
def create_metric(username: str, metric_type: str, date: str, value: str, source: Optional[str] = None) -> dict:
    """Create or upsert a metric entry (one per metric_type per day).

    metric_type: 'weight' | 'muscle_index' | 'body_measurements'
    date: YYYY-MM-DD
    value: JSON string — examples:
      weight:             '{"kg": 75.5}'
      muscle_index:       '{"index": 35}'
      body_measurements:  '{"waist_cm": 85, "chest_cm": 100}'
    source: 'device' | 'calculated' (optional)
    """
    with _db() as db:
        u = _user(db, username)
        try:
            d = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            raise ValueError("Invalid date format. Use YYYY-MM-DD.")
        try:
            value_dict = json.loads(value)
        except json.JSONDecodeError:
            raise ValueError("value must be a valid JSON string, e.g. '{\"kg\": 75.5}'")
        existing = db.query(MetricEntry).filter(
            MetricEntry.user_id == u.id,
            MetricEntry.metric_type == metric_type,
            MetricEntry.date == d,
        ).first()
        if existing:
            existing.value = value_dict
            existing.source = source
            db.commit()
            db.refresh(existing)
            e = existing
        else:
            e = MetricEntry(user_id=u.id, metric_type=metric_type, date=d, value=value_dict, source=source)
            db.add(e)
            db.commit()
            db.refresh(e)
        return {
            "id": e.id,
            "metric_type": e.metric_type,
            "date": e.date.isoformat(),
            "value": e.value,
            "source": e.source,
            "created_at": e.created_at.isoformat(),
        }


@mcp.tool()
def update_metric(
    username: str,
    metric_id: int,
    value: Optional[str] = None,
    date: Optional[str] = None,
    source: Optional[str] = None,
) -> dict:
    """Update a metric entry. value is a JSON string. For body_measurements, value is merged (partial update)."""
    with _db() as db:
        u = _user(db, username)
        e = db.query(MetricEntry).filter(MetricEntry.id == metric_id, MetricEntry.user_id == u.id).first()
        if not e:
            raise ValueError(f"Metric entry {metric_id} not found.")
        if value is not None:
            try:
                value_dict = json.loads(value)
            except json.JSONDecodeError:
                raise ValueError("value must be a valid JSON string.")
            if e.metric_type == "body_measurements" and isinstance(e.value, dict):
                e.value = {**e.value, **value_dict}
            else:
                e.value = value_dict
        if source is not None:
            e.source = source
        if date is not None:
            try:
                new_date = datetime.strptime(date, "%Y-%m-%d").date()
            except ValueError:
                raise ValueError("Invalid date format. Use YYYY-MM-DD.")
            if new_date != e.date:
                conflict = db.query(MetricEntry).filter(
                    MetricEntry.user_id == u.id,
                    MetricEntry.metric_type == e.metric_type,
                    MetricEntry.date == new_date,
                    MetricEntry.id != metric_id,
                ).first()
                if conflict:
                    raise ValueError(f"Entry already exists for {e.metric_type} on {date}.")
            e.date = new_date
        db.commit()
        db.refresh(e)
        return {
            "id": e.id,
            "metric_type": e.metric_type,
            "date": e.date.isoformat(),
            "value": e.value,
            "source": e.source,
            "created_at": e.created_at.isoformat(),
        }


@mcp.tool()
def delete_metric(username: str, metric_id: int) -> dict:
    """Delete a metric entry by id."""
    with _db() as db:
        u = _user(db, username)
        e = db.query(MetricEntry).filter(MetricEntry.id == metric_id, MetricEntry.user_id == u.id).first()
        if not e:
            raise ValueError(f"Metric entry {metric_id} not found.")
        db.delete(e)
        db.commit()
        return {"message": f"Metric entry {metric_id} deleted."}


# ─── Goals ────────────────────────────────────────────────────────────────────

@mcp.tool()
def list_goals(username: str, is_achieved: Optional[bool] = None) -> list:
    """List fitness goals for a user. Optionally filter by is_achieved (true/false)."""
    with _db() as db:
        u = _user(db, username)
        q = db.query(Goal).filter(Goal.user_id == u.id)
        if is_achieved is not None:
            q = q.filter(Goal.is_achieved == is_achieved)
        return [
            {
                "id": g.id,
                "title": g.title,
                "description": g.description,
                "target_date": g.target_date.isoformat() if g.target_date else None,
                "is_achieved": g.is_achieved,
                "created_at": g.created_at.isoformat(),
                "updated_at": g.updated_at.isoformat() if g.updated_at else None,
            }
            for g in q.order_by(Goal.created_at.desc()).all()
        ]


@mcp.tool()
def create_goal(
    username: str,
    title: str,
    description: Optional[str] = None,
    target_date: Optional[str] = None,
) -> dict:
    """Create a fitness goal for a user. target_date: YYYY-MM-DD (optional)."""
    with _db() as db:
        u = _user(db, username)
        td = date_type.fromisoformat(target_date) if target_date else None
        g = Goal(user_id=u.id, title=title, description=description, target_date=td)
        db.add(g)
        db.commit()
        db.refresh(g)
        return {
            "id": g.id,
            "title": g.title,
            "description": g.description,
            "target_date": g.target_date.isoformat() if g.target_date else None,
            "is_achieved": g.is_achieved,
            "created_at": g.created_at.isoformat(),
        }


@mcp.tool()
def update_goal(
    username: str,
    goal_id: int,
    title: Optional[str] = None,
    description: Optional[str] = None,
    target_date: Optional[str] = None,
    is_achieved: Optional[bool] = None,
) -> dict:
    """Update a goal by id. Only provided fields are changed."""
    with _db() as db:
        u = _user(db, username)
        g = db.query(Goal).filter(Goal.id == goal_id, Goal.user_id == u.id).first()
        if not g:
            raise ValueError(f"Goal {goal_id} not found.")
        if title is not None:
            g.title = title
        if description is not None:
            g.description = description
        if target_date is not None:
            g.target_date = date_type.fromisoformat(target_date)
        if is_achieved is not None:
            g.is_achieved = is_achieved
        db.commit()
        db.refresh(g)
        return {
            "id": g.id,
            "title": g.title,
            "description": g.description,
            "target_date": g.target_date.isoformat() if g.target_date else None,
            "is_achieved": g.is_achieved,
            "created_at": g.created_at.isoformat(),
            "updated_at": g.updated_at.isoformat() if g.updated_at else None,
        }


@mcp.tool()
def delete_goal(username: str, goal_id: int) -> dict:
    """Delete a goal by id."""
    with _db() as db:
        u = _user(db, username)
        g = db.query(Goal).filter(Goal.id == goal_id, Goal.user_id == u.id).first()
        if not g:
            raise ValueError(f"Goal {goal_id} not found.")
        db.delete(g)
        db.commit()
        return {"message": f"Goal {goal_id} deleted."}


# ─── Exercises ────────────────────────────────────────────────────────────────

@mcp.tool()
def list_exercises(username: str, muscle_group: Optional[str] = None, equipment: Optional[str] = None) -> list:
    """List all available exercises (global library + user's custom). Filter by muscle_group or equipment."""
    with _db() as db:
        u = _user(db, username)
        q = db.query(Exercise).filter(
            (Exercise.owner_id.is_(None)) | (Exercise.owner_id == u.id)
        )
        if muscle_group:
            q = q.filter(Exercise.muscle_group == muscle_group)
        if equipment:
            q = q.filter(Exercise.equipment == equipment)
        return [
            {
                "id": ex.id,
                "name": ex.name,
                "description": ex.description,
                "muscle_group": ex.muscle_group,
                "equipment": ex.equipment,
                "is_global": ex.owner_id is None,
            }
            for ex in q.order_by(Exercise.name).all()
        ]


@mcp.tool()
def create_exercise(
    username: str,
    name: str,
    description: Optional[str] = None,
    muscle_group: Optional[str] = None,
    equipment: Optional[str] = None,
) -> dict:
    """Create a custom exercise owned by the user."""
    with _db() as db:
        u = _user(db, username)
        ex = Exercise(name=name, description=description, muscle_group=muscle_group, equipment=equipment, owner_id=u.id)
        db.add(ex)
        db.commit()
        db.refresh(ex)
        return {
            "id": ex.id,
            "name": ex.name,
            "description": ex.description,
            "muscle_group": ex.muscle_group,
            "equipment": ex.equipment,
            "is_global": False,
        }


# ─── Workout Plans ────────────────────────────────────────────────────────────

def _plan_to_dict(plan: WorkoutPlan) -> dict:
    days = []
    for d in plan.days:
        days.append({
            "id": d.id,
            "day_number": d.day_number,
            "name": d.name,
            "is_rest_day": d.is_rest_day,
            "notes": d.notes,
            "exercises": [
                {
                    "id": pe.id,
                    "exercise_id": pe.exercise_id,
                    "exercise_name": pe.exercise.name,
                    "order": pe.order,
                    "sets": pe.sets,
                    "reps": pe.reps,
                    "weight_kg": pe.weight_kg,
                    "rest_seconds": pe.rest_seconds,
                    "notes": pe.notes,
                    "set_configs": pe.set_configs,
                }
                for pe in d.exercises
            ],
        })
    return {
        "id": plan.id,
        "name": plan.name,
        "description": plan.description,
        "duration_value": plan.duration_value,
        "duration_unit": plan.duration_unit,
        "start_date": plan.start_date.isoformat() if plan.start_date else None,
        "is_active": plan.is_active,
        "created_at": plan.created_at.isoformat(),
        "days": days,
    }


@mcp.tool()
def list_plans(username: str) -> list:
    """List all workout plans for a user (summary with day count)."""
    with _db() as db:
        u = _user(db, username)
        plans = db.query(WorkoutPlan).filter(WorkoutPlan.user_id == u.id).order_by(WorkoutPlan.created_at.desc()).all()
        result = []
        for p in plans:
            day_count = db.query(func.count(WorkoutPlanDay.id)).filter(WorkoutPlanDay.plan_id == p.id).scalar() or 0
            result.append({
                "id": p.id,
                "name": p.name,
                "description": p.description,
                "duration_value": p.duration_value,
                "duration_unit": p.duration_unit,
                "start_date": p.start_date.isoformat() if p.start_date else None,
                "is_active": p.is_active,
                "day_count": day_count,
                "created_at": p.created_at.isoformat(),
            })
        return result


@mcp.tool()
def get_plan(username: str, plan_id: int) -> dict:
    """Get a workout plan with all its days and exercises."""
    with _db() as db:
        u = _user(db, username)
        plan = db.query(WorkoutPlan).filter(WorkoutPlan.id == plan_id, WorkoutPlan.user_id == u.id).first()
        if not plan:
            raise ValueError(f"Plan {plan_id} not found.")
        return _plan_to_dict(plan)


@mcp.tool()
def create_plan(
    username: str,
    name: str,
    duration_value: int,
    duration_unit: str,
    description: Optional[str] = None,
) -> dict:
    """Create a workout plan for a user. duration_unit: 'weeks' | 'days' | 'months'."""
    with _db() as db:
        u = _user(db, username)
        plan = WorkoutPlan(
            user_id=u.id,
            name=name,
            description=description,
            duration_value=duration_value,
            duration_unit=duration_unit,
        )
        db.add(plan)
        db.commit()
        db.refresh(plan)
        return _plan_to_dict(plan)


@mcp.tool()
def update_plan(
    username: str,
    plan_id: int,
    name: str,
    duration_value: int,
    duration_unit: str,
    description: Optional[str] = None,
) -> dict:
    """Update a workout plan's metadata (name, description, duration)."""
    with _db() as db:
        u = _user(db, username)
        plan = db.query(WorkoutPlan).filter(WorkoutPlan.id == plan_id, WorkoutPlan.user_id == u.id).first()
        if not plan:
            raise ValueError(f"Plan {plan_id} not found.")
        plan.name = name
        plan.description = description
        plan.duration_value = duration_value
        plan.duration_unit = duration_unit
        db.commit()
        db.refresh(plan)
        return _plan_to_dict(plan)


@mcp.tool()
def delete_plan(username: str, plan_id: int) -> dict:
    """Delete a workout plan and all its days and exercises."""
    with _db() as db:
        u = _user(db, username)
        plan = db.query(WorkoutPlan).filter(WorkoutPlan.id == plan_id, WorkoutPlan.user_id == u.id).first()
        if not plan:
            raise ValueError(f"Plan {plan_id} not found.")
        db.delete(plan)
        db.commit()
        return {"message": f"Plan {plan_id} deleted."}


@mcp.tool()
def activate_plan(username: str, plan_id: int) -> dict:
    """Set a plan as active for a user (deactivates all others). Sets start_date to today."""
    with _db() as db:
        u = _user(db, username)
        plan = db.query(WorkoutPlan).filter(WorkoutPlan.id == plan_id, WorkoutPlan.user_id == u.id).first()
        if not plan:
            raise ValueError(f"Plan {plan_id} not found.")
        db.query(WorkoutPlan).filter(WorkoutPlan.user_id == u.id).update({"is_active": False})
        plan.is_active = True
        plan.start_date = date_type.today()
        db.commit()
        db.refresh(plan)
        return _plan_to_dict(plan)


# ─── Plan Days ────────────────────────────────────────────────────────────────

@mcp.tool()
def create_plan_day(
    username: str,
    plan_id: int,
    day_number: int,
    name: Optional[str] = None,
    is_rest_day: bool = False,
    notes: Optional[str] = None,
) -> dict:
    """Add a day to a workout plan. day_number must be unique within the plan."""
    with _db() as db:
        u = _user(db, username)
        plan = db.query(WorkoutPlan).filter(WorkoutPlan.id == plan_id, WorkoutPlan.user_id == u.id).first()
        if not plan:
            raise ValueError(f"Plan {plan_id} not found.")
        if db.query(WorkoutPlanDay).filter(WorkoutPlanDay.plan_id == plan_id, WorkoutPlanDay.day_number == day_number).first():
            raise ValueError(f"Day {day_number} already exists in plan {plan_id}.")
        day = WorkoutPlanDay(plan_id=plan_id, day_number=day_number, name=name, is_rest_day=is_rest_day, notes=notes)
        db.add(day)
        db.commit()
        db.refresh(day)
        return {"id": day.id, "plan_id": day.plan_id, "day_number": day.day_number, "name": day.name, "is_rest_day": day.is_rest_day, "notes": day.notes, "exercises": []}


@mcp.tool()
def update_plan_day(
    username: str,
    plan_id: int,
    day_id: int,
    day_number: Optional[int] = None,
    name: Optional[str] = None,
    is_rest_day: Optional[bool] = None,
    notes: Optional[str] = None,
) -> dict:
    """Update a day in a workout plan."""
    with _db() as db:
        u = _user(db, username)
        plan = db.query(WorkoutPlan).filter(WorkoutPlan.id == plan_id, WorkoutPlan.user_id == u.id).first()
        if not plan:
            raise ValueError(f"Plan {plan_id} not found.")
        day = db.query(WorkoutPlanDay).filter(WorkoutPlanDay.id == day_id, WorkoutPlanDay.plan_id == plan_id).first()
        if not day:
            raise ValueError(f"Day {day_id} not found in plan {plan_id}.")
        if day_number is not None and day_number != day.day_number:
            if db.query(WorkoutPlanDay).filter(WorkoutPlanDay.plan_id == plan_id, WorkoutPlanDay.day_number == day_number).first():
                raise ValueError(f"Day number {day_number} already exists in this plan.")
            day.day_number = day_number
        if name is not None:
            day.name = name
        if is_rest_day is not None:
            day.is_rest_day = is_rest_day
        if notes is not None:
            day.notes = notes
        db.commit()
        db.refresh(day)
        return {
            "id": day.id,
            "plan_id": day.plan_id,
            "day_number": day.day_number,
            "name": day.name,
            "is_rest_day": day.is_rest_day,
            "notes": day.notes,
            "exercises": [
                {"id": pe.id, "exercise_id": pe.exercise_id, "exercise_name": pe.exercise.name, "order": pe.order, "sets": pe.sets, "reps": pe.reps, "weight_kg": pe.weight_kg, "rest_seconds": pe.rest_seconds, "notes": pe.notes}
                for pe in day.exercises
            ],
        }


@mcp.tool()
def delete_plan_day(username: str, plan_id: int, day_id: int) -> dict:
    """Delete a day (and all its exercises) from a workout plan."""
    with _db() as db:
        u = _user(db, username)
        plan = db.query(WorkoutPlan).filter(WorkoutPlan.id == plan_id, WorkoutPlan.user_id == u.id).first()
        if not plan:
            raise ValueError(f"Plan {plan_id} not found.")
        day = db.query(WorkoutPlanDay).filter(WorkoutPlanDay.id == day_id, WorkoutPlanDay.plan_id == plan_id).first()
        if not day:
            raise ValueError(f"Day {day_id} not found in plan {plan_id}.")
        db.delete(day)
        db.commit()
        return {"message": f"Day {day_id} deleted from plan {plan_id}."}


# ─── Plan Day Exercises ───────────────────────────────────────────────────────

@mcp.tool()
def add_exercise_to_day(
    username: str,
    plan_id: int,
    day_id: int,
    exercise_id: int,
    order: int = 1,
    sets: Optional[int] = None,
    reps: Optional[int] = None,
    weight_kg: Optional[float] = None,
    rest_seconds: Optional[int] = None,
    notes: Optional[str] = None,
) -> dict:
    """Add an exercise to a plan day. Use list_exercises to find exercise_id."""
    with _db() as db:
        u = _user(db, username)
        plan = db.query(WorkoutPlan).filter(WorkoutPlan.id == plan_id, WorkoutPlan.user_id == u.id).first()
        if not plan:
            raise ValueError(f"Plan {plan_id} not found.")
        day = db.query(WorkoutPlanDay).filter(WorkoutPlanDay.id == day_id, WorkoutPlanDay.plan_id == plan_id).first()
        if not day:
            raise ValueError(f"Day {day_id} not found in plan {plan_id}.")
        ex = db.query(Exercise).filter(
            Exercise.id == exercise_id,
            (Exercise.owner_id.is_(None)) | (Exercise.owner_id == u.id),
        ).first()
        if not ex:
            raise ValueError(f"Exercise {exercise_id} not found or not available.")
        entry = WorkoutPlanExercise(
            plan_day_id=day_id,
            exercise_id=exercise_id,
            order=order,
            sets=sets,
            reps=reps,
            weight_kg=weight_kg,
            rest_seconds=rest_seconds,
            notes=notes,
        )
        db.add(entry)
        db.commit()
        db.refresh(entry)
        return {
            "id": entry.id,
            "plan_day_id": entry.plan_day_id,
            "exercise_id": entry.exercise_id,
            "exercise_name": entry.exercise.name,
            "order": entry.order,
            "sets": entry.sets,
            "reps": entry.reps,
            "weight_kg": entry.weight_kg,
            "rest_seconds": entry.rest_seconds,
            "notes": entry.notes,
        }


@mcp.tool()
def update_day_exercise(
    username: str,
    plan_id: int,
    day_id: int,
    entry_id: int,
    exercise_id: Optional[int] = None,
    order: Optional[int] = None,
    sets: Optional[int] = None,
    reps: Optional[int] = None,
    weight_kg: Optional[float] = None,
    rest_seconds: Optional[int] = None,
    notes: Optional[str] = None,
) -> dict:
    """Update an exercise entry in a plan day."""
    with _db() as db:
        u = _user(db, username)
        plan = db.query(WorkoutPlan).filter(WorkoutPlan.id == plan_id, WorkoutPlan.user_id == u.id).first()
        if not plan:
            raise ValueError(f"Plan {plan_id} not found.")
        day = db.query(WorkoutPlanDay).filter(WorkoutPlanDay.id == day_id, WorkoutPlanDay.plan_id == plan_id).first()
        if not day:
            raise ValueError(f"Day {day_id} not found.")
        entry = db.query(WorkoutPlanExercise).filter(
            WorkoutPlanExercise.id == entry_id, WorkoutPlanExercise.plan_day_id == day_id
        ).first()
        if not entry:
            raise ValueError(f"Exercise entry {entry_id} not found in day {day_id}.")
        if exercise_id is not None:
            ex = db.query(Exercise).filter(
                Exercise.id == exercise_id,
                (Exercise.owner_id.is_(None)) | (Exercise.owner_id == u.id),
            ).first()
            if not ex:
                raise ValueError(f"Exercise {exercise_id} not found or not available.")
            entry.exercise_id = exercise_id
        if order is not None:
            entry.order = order
        if sets is not None:
            entry.sets = sets
        if reps is not None:
            entry.reps = reps
        if weight_kg is not None:
            entry.weight_kg = weight_kg
        if rest_seconds is not None:
            entry.rest_seconds = rest_seconds
        if notes is not None:
            entry.notes = notes
        db.commit()
        db.refresh(entry)
        return {
            "id": entry.id,
            "plan_day_id": entry.plan_day_id,
            "exercise_id": entry.exercise_id,
            "exercise_name": entry.exercise.name,
            "order": entry.order,
            "sets": entry.sets,
            "reps": entry.reps,
            "weight_kg": entry.weight_kg,
            "rest_seconds": entry.rest_seconds,
            "notes": entry.notes,
        }


@mcp.tool()
def remove_exercise_from_day(username: str, plan_id: int, day_id: int, entry_id: int) -> dict:
    """Remove an exercise from a plan day."""
    with _db() as db:
        u = _user(db, username)
        plan = db.query(WorkoutPlan).filter(WorkoutPlan.id == plan_id, WorkoutPlan.user_id == u.id).first()
        if not plan:
            raise ValueError(f"Plan {plan_id} not found.")
        day = db.query(WorkoutPlanDay).filter(WorkoutPlanDay.id == day_id, WorkoutPlanDay.plan_id == plan_id).first()
        if not day:
            raise ValueError(f"Day {day_id} not found.")
        entry = db.query(WorkoutPlanExercise).filter(
            WorkoutPlanExercise.id == entry_id, WorkoutPlanExercise.plan_day_id == day_id
        ).first()
        if not entry:
            raise ValueError(f"Exercise entry {entry_id} not found in day {day_id}.")
        db.delete(entry)
        db.commit()
        return {"message": f"Exercise entry {entry_id} removed from day {day_id}."}
