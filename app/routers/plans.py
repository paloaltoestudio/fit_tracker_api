"""Workout plans and exercises API. All routes require JWT."""
from datetime import date, datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models import (
    User,
    Exercise,
    WorkoutPlan,
    WorkoutPlanDay,
    WorkoutPlanExercise,
)
from app.schemas import (
    ExerciseCreate,
    ExerciseUpdate,
    ExerciseResponse,
    WorkoutPlanCreate,
    WorkoutPlanSummary,
    WorkoutPlanResponse,
    WorkoutPlanDayCreate,
    WorkoutPlanDayUpdate,
    WorkoutPlanDayResponse,
    WorkoutPlanExerciseCreate,
    WorkoutPlanExerciseUpdate,
    WorkoutPlanExerciseResponse,
)
from app.auth import get_current_user_id

router = APIRouter()
security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    token = credentials.credentials
    user_id = get_current_user_id(token)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def _exercise_visible_to_user(exercise: Exercise, user: User) -> bool:
    return exercise.owner_id is None or exercise.owner_id == user.id


def _exercise_editable_by_user(exercise: Exercise, user: User) -> bool:
    return exercise.owner_id is not None and exercise.owner_id == user.id


def _to_exercise_response(ex: Exercise) -> ExerciseResponse:
    return ExerciseResponse(
        id=ex.id,
        name=ex.name,
        description=ex.description,
        muscle_group=ex.muscle_group,
        equipment=ex.equipment,
        owner_id=ex.owner_id,
        is_global=ex.owner_id is None,
        created_at=ex.created_at.isoformat(),
    )


def _to_plan_summary(plan: WorkoutPlan, day_count: int) -> WorkoutPlanSummary:
    return WorkoutPlanSummary(
        id=plan.id,
        user_id=plan.user_id,
        name=plan.name,
        description=plan.description,
        duration_value=plan.duration_value,
        duration_unit=plan.duration_unit,
        start_date=plan.start_date.isoformat() if plan.start_date else None,
        is_active=plan.is_active,
        created_at=plan.created_at.isoformat(),
        updated_at=plan.updated_at.isoformat() if plan.updated_at else None,
        day_count=day_count,
    )


def _to_plan_response(plan: WorkoutPlan) -> WorkoutPlanResponse:
    days_data = []
    for d in plan.days:
        exercises_data = [
            WorkoutPlanExerciseResponse(
                id=pe.id,
                plan_day_id=pe.plan_day_id,
                exercise_id=pe.exercise_id,
                exercise=_to_exercise_response(pe.exercise),
                order=pe.order,
                sets=pe.sets,
                reps=pe.reps,
                weight_kg=pe.weight_kg,
                rest_seconds=pe.rest_seconds,
                notes=pe.notes,
                set_configs=pe.set_configs,
            )
            for pe in d.exercises
        ]
        days_data.append(
            WorkoutPlanDayResponse(
                id=d.id,
                plan_id=d.plan_id,
                day_number=d.day_number,
                name=d.name,
                is_rest_day=d.is_rest_day,
                notes=d.notes,
                exercises=exercises_data,
            )
        )
    return WorkoutPlanResponse(
        id=plan.id,
        user_id=plan.user_id,
        name=plan.name,
        description=plan.description,
        duration_value=plan.duration_value,
        duration_unit=plan.duration_unit,
        start_date=plan.start_date.isoformat() if plan.start_date else None,
        is_active=plan.is_active,
        created_at=plan.created_at.isoformat(),
        updated_at=plan.updated_at.isoformat() if plan.updated_at else None,
        days=days_data,
    )


def _to_day_response(day: WorkoutPlanDay) -> WorkoutPlanDayResponse:
    exercises_data = [
        WorkoutPlanExerciseResponse(
            id=pe.id,
            plan_day_id=pe.plan_day_id,
            exercise_id=pe.exercise_id,
            exercise=_to_exercise_response(pe.exercise),
            order=pe.order,
            sets=pe.sets,
            reps=pe.reps,
            weight_kg=pe.weight_kg,
            rest_seconds=pe.rest_seconds,
            notes=pe.notes,
            set_configs=pe.set_configs,
        )
        for pe in day.exercises
    ]
    return WorkoutPlanDayResponse(
        id=day.id,
        plan_id=day.plan_id,
        day_number=day.day_number,
        name=day.name,
        is_rest_day=day.is_rest_day,
        notes=day.notes,
        exercises=exercises_data,
    )


# ---- Exercises ----

@router.get("/exercises", response_model=List[ExerciseResponse])
def list_exercises(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    muscle_group: Optional[str] = Query(None),
    equipment: Optional[str] = Query(None),
):
    """Returns global exercises + current user's custom exercises. Optional filters."""
    q = db.query(Exercise).filter(
        (Exercise.owner_id.is_(None)) | (Exercise.owner_id == current_user.id)
    )
    if muscle_group is not None:
        q = q.filter(Exercise.muscle_group == muscle_group)
    if equipment is not None:
        q = q.filter(Exercise.equipment == equipment)
    exercises = q.order_by(Exercise.name).all()
    return [_to_exercise_response(ex) for ex in exercises]


@router.post("/exercises", response_model=ExerciseResponse, status_code=status.HTTP_201_CREATED)
def create_exercise(
    data: ExerciseCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a custom exercise owned by the current user."""
    ex = Exercise(
        name=data.name,
        description=data.description,
        muscle_group=data.muscle_group,
        equipment=data.equipment,
        owner_id=current_user.id,
    )
    db.add(ex)
    db.commit()
    db.refresh(ex)
    return _to_exercise_response(ex)


@router.get("/exercises/{exercise_id}", response_model=ExerciseResponse)
def get_exercise(
    exercise_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ex = db.query(Exercise).filter(Exercise.id == exercise_id).first()
    if not ex or not _exercise_visible_to_user(ex, current_user):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exercise not found")
    return _to_exercise_response(ex)


@router.put("/exercises/{exercise_id}", response_model=ExerciseResponse)
def update_exercise(
    exercise_id: int,
    data: ExerciseUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ex = db.query(Exercise).filter(Exercise.id == exercise_id).first()
    if not ex or not _exercise_visible_to_user(ex, current_user):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exercise not found")
    if not _exercise_editable_by_user(ex, current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot edit global exercise")
    if data.name is not None:
        ex.name = data.name
    if data.description is not None:
        ex.description = data.description
    if data.muscle_group is not None:
        ex.muscle_group = data.muscle_group
    if data.equipment is not None:
        ex.equipment = data.equipment
    db.commit()
    db.refresh(ex)
    return _to_exercise_response(ex)


@router.delete("/exercises/{exercise_id}", status_code=status.HTTP_200_OK)
def delete_exercise(
    exercise_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ex = db.query(Exercise).filter(Exercise.id == exercise_id).first()
    if not ex or not _exercise_visible_to_user(ex, current_user):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exercise not found")
    if not _exercise_editable_by_user(ex, current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot delete global exercise")
    ref_count = db.query(WorkoutPlanExercise).filter(WorkoutPlanExercise.exercise_id == exercise_id).count()
    if ref_count > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot delete exercise: it is used in {ref_count} workout plan entry/entries. Remove it from all plans first.",
        )
    db.delete(ex)
    db.commit()
    return {"message": "Exercise deleted"}


# ---- Workout Plans ----

@router.get("/plans", response_model=List[WorkoutPlanSummary])
def list_plans(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    plans = db.query(WorkoutPlan).filter(WorkoutPlan.user_id == current_user.id).order_by(WorkoutPlan.created_at.desc()).all()
    result = []
    for p in plans:
        day_count = db.query(func.count(WorkoutPlanDay.id)).filter(WorkoutPlanDay.plan_id == p.id).scalar() or 0
        result.append(_to_plan_summary(p, day_count))
    return result


@router.post("/plans", response_model=WorkoutPlanResponse, status_code=status.HTTP_201_CREATED)
def create_plan(
    data: WorkoutPlanCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    plan = WorkoutPlan(
        user_id=current_user.id,
        name=data.name,
        description=data.description,
        duration_value=data.duration_value,
        duration_unit=data.duration_unit,
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return _to_plan_response(plan)


@router.get("/plans/{plan_id}", response_model=WorkoutPlanResponse)
def get_plan(
    plan_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    plan = db.query(WorkoutPlan).filter(WorkoutPlan.id == plan_id).first()
    if not plan or plan.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
    return _to_plan_response(plan)


@router.put("/plans/{plan_id}", response_model=WorkoutPlanResponse)
def update_plan(
    plan_id: int,
    data: WorkoutPlanCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    plan = db.query(WorkoutPlan).filter(WorkoutPlan.id == plan_id).first()
    if not plan or plan.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
    plan.name = data.name
    plan.description = data.description
    plan.duration_value = data.duration_value
    plan.duration_unit = data.duration_unit
    db.commit()
    db.refresh(plan)
    return _to_plan_response(plan)


@router.delete("/plans/{plan_id}", status_code=status.HTTP_200_OK)
def delete_plan(
    plan_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    plan = db.query(WorkoutPlan).filter(WorkoutPlan.id == plan_id).first()
    if not plan or plan.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
    db.delete(plan)
    db.commit()
    return {"message": "Plan deleted"}


@router.post("/plans/{plan_id}/activate", response_model=WorkoutPlanResponse)
def activate_plan(
    plan_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    plan = db.query(WorkoutPlan).filter(WorkoutPlan.id == plan_id).first()
    if not plan or plan.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
    db.query(WorkoutPlan).filter(WorkoutPlan.user_id == current_user.id).update({"is_active": False})
    plan.is_active = True
    plan.start_date = date.today()
    db.commit()
    db.refresh(plan)
    return _to_plan_response(plan)


# ---- Plan Days ----

def _get_plan_and_day(plan_id: int, day_id: int, user_id: int, db: Session):
    plan = db.query(WorkoutPlan).filter(WorkoutPlan.id == plan_id, WorkoutPlan.user_id == user_id).first()
    if not plan:
        return None, None
    day = db.query(WorkoutPlanDay).filter(WorkoutPlanDay.id == day_id, WorkoutPlanDay.plan_id == plan_id).first()
    return plan, day


@router.post("/plans/{plan_id}/days", response_model=WorkoutPlanDayResponse, status_code=status.HTTP_201_CREATED)
def create_plan_day(
    plan_id: int,
    data: WorkoutPlanDayCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    plan = db.query(WorkoutPlan).filter(WorkoutPlan.id == plan_id, WorkoutPlan.user_id == current_user.id).first()
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
    existing = db.query(WorkoutPlanDay).filter(WorkoutPlanDay.plan_id == plan_id, WorkoutPlanDay.day_number == data.day_number).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Day number {data.day_number} already exists in this plan")
    day = WorkoutPlanDay(
        plan_id=plan_id,
        day_number=data.day_number,
        name=data.name,
        is_rest_day=data.is_rest_day,
        notes=data.notes,
    )
    db.add(day)
    db.commit()
    db.refresh(day)
    return _to_day_response(day)


@router.put("/plans/{plan_id}/days/{day_id}", response_model=WorkoutPlanDayResponse)
def update_plan_day(
    plan_id: int,
    day_id: int,
    data: WorkoutPlanDayUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    plan, day = _get_plan_and_day(plan_id, day_id, current_user.id, db)
    if not plan or not day:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan or day not found")
    if data.day_number is not None and data.day_number != day.day_number:
        existing = db.query(WorkoutPlanDay).filter(WorkoutPlanDay.plan_id == plan_id, WorkoutPlanDay.day_number == data.day_number).first()
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Day number {data.day_number} already exists")
        day.day_number = data.day_number
    if data.name is not None:
        day.name = data.name
    if data.is_rest_day is not None:
        day.is_rest_day = data.is_rest_day
    if data.notes is not None:
        day.notes = data.notes
    db.commit()
    db.refresh(day)
    return _to_day_response(day)


@router.delete("/plans/{plan_id}/days/{day_id}", status_code=status.HTTP_200_OK)
def delete_plan_day(
    plan_id: int,
    day_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    plan, day = _get_plan_and_day(plan_id, day_id, current_user.id, db)
    if not plan or not day:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan or day not found")
    db.delete(day)
    db.commit()
    return {"message": "Day deleted"}


# ---- Plan Day Exercises ----

def _get_plan_day_and_entry(plan_id: int, day_id: int, entry_id: int, user_id: int, db: Session):
    plan = db.query(WorkoutPlan).filter(WorkoutPlan.id == plan_id, WorkoutPlan.user_id == user_id).first()
    if not plan:
        return None, None, None
    day = db.query(WorkoutPlanDay).filter(WorkoutPlanDay.id == day_id, WorkoutPlanDay.plan_id == plan_id).first()
    if not day:
        return plan, None, None
    entry = db.query(WorkoutPlanExercise).filter(WorkoutPlanExercise.id == entry_id, WorkoutPlanExercise.plan_day_id == day_id).first()
    return plan, day, entry


@router.post("/plans/{plan_id}/days/{day_id}/exercises", response_model=WorkoutPlanExerciseResponse, status_code=status.HTTP_201_CREATED)
def add_plan_day_exercise(
    plan_id: int,
    day_id: int,
    data: WorkoutPlanExerciseCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    plan, day = _get_plan_and_day(plan_id, day_id, current_user.id, db)
    if not plan or not day:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan or day not found")
    ex = db.query(Exercise).filter(Exercise.id == data.exercise_id).first()
    if not ex or not _exercise_visible_to_user(ex, current_user):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Exercise not found or not available to you")
    entry = WorkoutPlanExercise(
        plan_day_id=day_id,
        exercise_id=data.exercise_id,
        order=data.order,
        sets=data.sets,
        reps=data.reps,
        weight_kg=data.weight_kg,
        rest_seconds=data.rest_seconds,
        notes=data.notes,
        set_configs=[s.model_dump(exclude_none=True) for s in data.set_configs] if data.set_configs is not None else None,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return WorkoutPlanExerciseResponse(
        id=entry.id,
        plan_day_id=entry.plan_day_id,
        exercise_id=entry.exercise_id,
        exercise=_to_exercise_response(entry.exercise),
        order=entry.order,
        sets=entry.sets,
        reps=entry.reps,
        weight_kg=entry.weight_kg,
        rest_seconds=entry.rest_seconds,
        notes=entry.notes,
        set_configs=entry.set_configs,
    )


@router.put("/plans/{plan_id}/days/{day_id}/exercises/{entry_id}", response_model=WorkoutPlanExerciseResponse)
def update_plan_day_exercise(
    plan_id: int,
    day_id: int,
    entry_id: int,
    data: WorkoutPlanExerciseUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    plan, day, entry = _get_plan_day_and_entry(plan_id, day_id, entry_id, current_user.id, db)
    if not plan or not day or not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan, day, or exercise entry not found")
    if data.exercise_id is not None:
        ex = db.query(Exercise).filter(Exercise.id == data.exercise_id).first()
        if not ex or not _exercise_visible_to_user(ex, current_user):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Exercise not found or not available")
        entry.exercise_id = data.exercise_id
    if data.order is not None:
        entry.order = data.order
    if data.sets is not None:
        entry.sets = data.sets
    if data.reps is not None:
        entry.reps = data.reps
    if data.weight_kg is not None:
        entry.weight_kg = data.weight_kg
    if data.rest_seconds is not None:
        entry.rest_seconds = data.rest_seconds
    if data.notes is not None:
        entry.notes = data.notes
    if data.set_configs is not None:
        entry.set_configs = [s.model_dump(exclude_none=True) for s in data.set_configs]
    db.commit()
    db.refresh(entry)
    return WorkoutPlanExerciseResponse(
        id=entry.id,
        plan_day_id=entry.plan_day_id,
        exercise_id=entry.exercise_id,
        exercise=_to_exercise_response(entry.exercise),
        order=entry.order,
        sets=entry.sets,
        reps=entry.reps,
        weight_kg=entry.weight_kg,
        rest_seconds=entry.rest_seconds,
        notes=entry.notes,
        set_configs=entry.set_configs,
    )


@router.delete("/plans/{plan_id}/days/{day_id}/exercises/{entry_id}", status_code=status.HTTP_200_OK)
def delete_plan_day_exercise(
    plan_id: int,
    day_id: int,
    entry_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    plan, day, entry = _get_plan_day_and_entry(plan_id, day_id, entry_id, current_user.id, db)
    if not plan or not day or not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan, day, or exercise entry not found")
    db.delete(entry)
    db.commit()
    return {"message": "Exercise entry removed from day"}
