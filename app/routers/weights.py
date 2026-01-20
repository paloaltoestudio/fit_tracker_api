from datetime import date, datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Weight, User
from app.schemas import WeightCreate, WeightUpdate, WeightResponse
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


def verify_weight_ownership(weight_id: int, current_user: User, db: Session) -> Weight:
    """Verify that the weight entry exists and belongs to the current user"""
    weight = db.query(Weight).filter(Weight.id == weight_id).first()
    
    if not weight:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Weight entry not found"
        )
    
    if weight.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this weight entry"
        )
    
    return weight


@router.post("/weights", response_model=WeightResponse, status_code=status.HTTP_201_CREATED)
async def create_weight(
    weight_data: WeightCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Add a historical weight entry for the authenticated user
    """
    try:
        # Parse the date string to date object
        weight_date = datetime.strptime(weight_data.date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid date format. Use YYYY-MM-DD format."
        )
    
    # Check if weight entry already exists for this date
    existing_weight = db.query(Weight).filter(
        Weight.user_id == current_user.id,
        Weight.date == weight_date
    ).first()
    
    if existing_weight:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Weight entry already exists for date {weight_data.date}. Use PUT /weights/{existing_weight.id} to update it."
        )
    
    # Create new weight entry
    new_weight = Weight(
        user_id=current_user.id,
        weight=weight_data.weight,
        date=weight_date
    )
    
    db.add(new_weight)
    db.commit()
    db.refresh(new_weight)
    
    return WeightResponse(
        id=new_weight.id,
        user_id=new_weight.user_id,
        weight=new_weight.weight,
        date=new_weight.date.isoformat(),
        created_at=new_weight.created_at.isoformat()
    )


@router.get("/weights", response_model=List[WeightResponse])
async def get_weights(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all weight entries for the authenticated user, ordered by date (newest first)
    """
    weights = db.query(Weight).filter(
        Weight.user_id == current_user.id
    ).order_by(Weight.date.desc()).all()
    
    return [
        WeightResponse(
            id=w.id,
            user_id=w.user_id,
            weight=w.weight,
            date=w.date.isoformat(),
            created_at=w.created_at.isoformat()
        )
        for w in weights
    ]


@router.get("/weights/{weight_id}", response_model=WeightResponse)
async def get_weight(
    weight_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get a specific weight entry by ID for the authenticated user
    """
    weight = verify_weight_ownership(weight_id, current_user, db)
    
    return WeightResponse(
        id=weight.id,
        user_id=weight.user_id,
        weight=weight.weight,
        date=weight.date.isoformat(),
        created_at=weight.created_at.isoformat()
    )


@router.put("/weights/{weight_id}", response_model=WeightResponse)
async def update_weight(
    weight_id: int,
    weight_data: WeightUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update a weight entry by ID. Cannot create duplicate entry for the same date.
    """
    weight = verify_weight_ownership(weight_id, current_user, db)
    
    # Track if date is being changed
    new_date = None
    if weight_data.date:
        try:
            new_date = datetime.strptime(weight_data.date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid date format. Use YYYY-MM-DD format."
            )
        
        # If date is being changed, check if another entry already exists for that date
        if new_date != weight.date:
            existing_weight = db.query(Weight).filter(
                Weight.user_id == current_user.id,
                Weight.date == new_date,
                Weight.id != weight_id  # Exclude current entry
            ).first()
            
            if existing_weight:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Weight entry already exists for date {weight_data.date}. Cannot update to a date that already has an entry."
                )
    
    # Update weight value if provided
    if weight_data.weight is not None:
        weight.weight = weight_data.weight
    
    # Update date if provided
    if new_date is not None:
        weight.date = new_date
    
    db.commit()
    db.refresh(weight)
    
    return WeightResponse(
        id=weight.id,
        user_id=weight.user_id,
        weight=weight.weight,
        date=weight.date.isoformat(),
        created_at=weight.created_at.isoformat()
    )


@router.delete("/weights/{weight_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_weight(
    weight_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a weight entry by ID for the authenticated user
    """
    weight = verify_weight_ownership(weight_id, current_user, db)
    
    db.delete(weight)
    db.commit()
    
    return None
