"""Goals API. All routes require JWT."""
from datetime import date
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, Goal
from app.schemas import GoalCreate, GoalUpdate, GoalResponse
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


def _to_response(goal: Goal) -> GoalResponse:
    return GoalResponse(
        id=goal.id,
        user_id=goal.user_id,
        title=goal.title,
        description=goal.description,
        target_date=goal.target_date.isoformat() if goal.target_date else None,
        is_achieved=goal.is_achieved,
        created_at=goal.created_at.isoformat(),
        updated_at=goal.updated_at.isoformat() if goal.updated_at else None,
    )


@router.get("/goals", response_model=List[GoalResponse])
def list_goals(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    is_achieved: bool | None = Query(None, description="Filter by achieved status"),
):
    q = db.query(Goal).filter(Goal.user_id == current_user.id)
    if is_achieved is not None:
        q = q.filter(Goal.is_achieved == is_achieved)
    return [_to_response(g) for g in q.order_by(Goal.created_at.desc()).all()]


@router.post("/goals", response_model=GoalResponse, status_code=status.HTTP_201_CREATED)
def create_goal(
    data: GoalCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    target_date = date.fromisoformat(data.target_date) if data.target_date else None
    goal = Goal(
        user_id=current_user.id,
        title=data.title,
        description=data.description,
        target_date=target_date,
    )
    db.add(goal)
    db.commit()
    db.refresh(goal)
    return _to_response(goal)


@router.get("/goals/{goal_id}", response_model=GoalResponse)
def get_goal(
    goal_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    goal = db.query(Goal).filter(Goal.id == goal_id, Goal.user_id == current_user.id).first()
    if not goal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found")
    return _to_response(goal)


@router.put("/goals/{goal_id}", response_model=GoalResponse)
def update_goal(
    goal_id: int,
    data: GoalUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    goal = db.query(Goal).filter(Goal.id == goal_id, Goal.user_id == current_user.id).first()
    if not goal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found")
    if data.title is not None:
        goal.title = data.title
    if data.description is not None:
        goal.description = data.description
    if data.target_date is not None:
        goal.target_date = date.fromisoformat(data.target_date)
    if data.is_achieved is not None:
        goal.is_achieved = data.is_achieved
    db.commit()
    db.refresh(goal)
    return _to_response(goal)


@router.delete("/goals/{goal_id}", status_code=status.HTTP_200_OK)
def delete_goal(
    goal_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    goal = db.query(Goal).filter(Goal.id == goal_id, Goal.user_id == current_user.id).first()
    if not goal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found")
    db.delete(goal)
    db.commit()
    return {"message": "Goal deleted"}
