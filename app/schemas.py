from pydantic import BaseModel, Field, field_validator
from typing import Optional


class UserLogin(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6, max_length=72)
    
    @field_validator('password')
    @classmethod
    def validate_password_length(cls, v: str) -> str:
        # Bcrypt has a 72-byte limit
        if len(v.encode('utf-8')) > 72:
            raise ValueError('Password cannot exceed 72 bytes. Please use a shorter password.')
        return v


class UserResponse(BaseModel):
    id: int
    username: str

    class Config:
        from_attributes = True


class WeightCreate(BaseModel):
    weight: float = Field(..., gt=0, description="Weight in kg")
    date: str = Field(..., description="Date in YYYY-MM-DD format")


class WeightUpdate(BaseModel):
    weight: Optional[float] = Field(None, gt=0, description="Weight in kg")
    date: Optional[str] = Field(None, description="Date in YYYY-MM-DD format")


class WeightResponse(BaseModel):
    id: int
    user_id: int
    weight: float
    date: str
    created_at: str

    class Config:
        from_attributes = True
