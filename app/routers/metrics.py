from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import MetricEntry, User
from app.schemas import MetricCreate, MetricUpdate, MetricResponse, validate_metric_value
from app.auth import get_current_user_id

router = APIRouter()
security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Get current authenticated user from JWT token"""
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


def _verify_metric_ownership(metric_id: int, current_user: User, db: Session) -> MetricEntry:
    """Verify that the metric entry exists and belongs to the current user."""
    entry = db.query(MetricEntry).filter(MetricEntry.id == metric_id).first()

    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Metric entry not found")

    if entry.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this metric entry",
        )

    return entry


def _metric_to_response(entry: MetricEntry) -> MetricResponse:
    return MetricResponse(
        id=entry.id,
        user_id=entry.user_id,
        metric_type=entry.metric_type,
        date=entry.date.isoformat(),
        value=entry.value,
        created_at=entry.created_at.isoformat(),
    )


@router.post("/metrics", response_model=MetricResponse, status_code=status.HTTP_201_CREATED)
async def create_metric(
    data: MetricCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create or update a metric entry. One entry per (user, metric_type, date).
    For weight: value = {"kg": 55}. For muscle_index: value = {"index": 10}.
    """
    try:
        metric_date = datetime.strptime(data.date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid date format. Use YYYY-MM-DD.",
        )

    existing = (
        db.query(MetricEntry)
        .filter(
            MetricEntry.user_id == current_user.id,
            MetricEntry.metric_type == data.metric_type,
            MetricEntry.date == metric_date,
        )
        .first()
    )

    if existing:
        existing.value = data.value
        db.commit()
        db.refresh(existing)
        return _metric_to_response(existing)

    entry = MetricEntry(
        user_id=current_user.id,
        metric_type=data.metric_type,
        date=metric_date,
        value=data.value,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return _metric_to_response(entry)


@router.get("/metrics", response_model=List[MetricResponse])
async def list_metrics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    metric_type: Optional[str] = Query(None, description="Filter by metric_type (weight, muscle_index)"),
    date_from: Optional[str] = Query(None, description="Filter from date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="Filter to date (YYYY-MM-DD)"),
):
    """
    List metric entries for the authenticated user. Optionally filter by metric_type and date range.
    """
    query = db.query(MetricEntry).filter(MetricEntry.user_id == current_user.id)

    if metric_type:
        query = query.filter(MetricEntry.metric_type == metric_type)

    if date_from:
        try:
            from_date = datetime.strptime(date_from, "%Y-%m-%d").date()
            query = query.filter(MetricEntry.date >= from_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date_from format. Use YYYY-MM-DD.")

    if date_to:
        try:
            to_date = datetime.strptime(date_to, "%Y-%m-%d").date()
            query = query.filter(MetricEntry.date <= to_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date_to format. Use YYYY-MM-DD.")

    entries = query.order_by(MetricEntry.date.desc()).all()
    return [_metric_to_response(e) for e in entries]


@router.get("/metrics/{metric_id}", response_model=MetricResponse)
async def get_metric(
    metric_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a single metric entry by ID."""
    entry = _verify_metric_ownership(metric_id, current_user, db)
    return _metric_to_response(entry)


@router.put("/metrics/{metric_id}", response_model=MetricResponse)
async def update_metric(
    metric_id: int,
    data: MetricUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update a metric entry. If changing date, the new date must not have an existing entry
    for the same metric_type.
    """
    entry = _verify_metric_ownership(metric_id, current_user, db)

    if data.value is not None:
        entry.value = validate_metric_value(entry.metric_type, data.value)

    if data.date is not None:
        try:
            new_date = datetime.strptime(data.date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")

        if new_date != entry.date:
            existing = (
                db.query(MetricEntry)
                .filter(
                    MetricEntry.user_id == current_user.id,
                    MetricEntry.metric_type == entry.metric_type,
                    MetricEntry.date == new_date,
                    MetricEntry.id != metric_id,
                )
                .first()
            )
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Entry already exists for {entry.metric_type} on {data.date}.",
                )
            entry.date = new_date

    db.commit()
    db.refresh(entry)
    return _metric_to_response(entry)


@router.delete("/metrics/{metric_id}", status_code=status.HTTP_200_OK)
async def delete_metric(
    metric_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a metric entry."""
    entry = _verify_metric_ownership(metric_id, current_user, db)
    db.delete(entry)
    db.commit()
    return {"message": f"Metric entry with id {metric_id} has been successfully deleted"}
