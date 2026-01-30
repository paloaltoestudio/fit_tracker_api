from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User
from app.schemas import ProfileResponse, ProfileUpdate
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


@router.get("/profile", response_model=ProfileResponse)
async def get_profile(
    current_user: User = Depends(get_current_user)
):
    """
    Get the profile of the authenticated user
    """
    return ProfileResponse(
        id=current_user.id,
        username=current_user.username,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        age=current_user.age,
        height_cm=current_user.height_cm,
        gender=current_user.gender
    )


@router.put("/profile", response_model=ProfileResponse)
async def update_profile(
    profile_data: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update the profile of the authenticated user
    """
    # Update fields if provided
    if profile_data.first_name is not None:
        current_user.first_name = profile_data.first_name
    
    if profile_data.last_name is not None:
        current_user.last_name = profile_data.last_name
    
    if profile_data.age is not None:
        current_user.age = profile_data.age
    
    if profile_data.height_cm is not None:
        current_user.height_cm = profile_data.height_cm
    
    if profile_data.gender is not None:
        current_user.gender = profile_data.gender
    
    db.commit()
    db.refresh(current_user)
    
    return ProfileResponse(
        id=current_user.id,
        username=current_user.username,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        age=current_user.age,
        height_cm=current_user.height_cm,
        gender=current_user.gender
    )
