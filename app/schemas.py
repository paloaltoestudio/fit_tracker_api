from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional, Literal, Any


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


class ProfileResponse(BaseModel):
    id: int
    username: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    age: Optional[int] = None
    height_cm: Optional[float] = None
    gender: Optional[str] = None

    class Config:
        from_attributes = True


class ProfileUpdate(BaseModel):
    first_name: Optional[str] = Field(None, max_length=50)
    last_name: Optional[str] = Field(None, max_length=50)
    age: Optional[int] = Field(None, ge=1, le=150)
    height_cm: Optional[float] = Field(None, gt=0, le=300, description="Height in cm")
    gender: Optional[Literal["Male", "Female"]] = None


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


# --- Metrics (flexible per metric_type) ---

METRIC_TYPES = ("weight", "muscle_index")

# Value schemas per metric type (for validation)
class WeightValue(BaseModel):
    kg: float = Field(..., gt=0, description="Weight in kg")


class MuscleIndexValue(BaseModel):
    index: float = Field(..., ge=0, le=100, description="Muscle index (0-100)")


def validate_metric_value(metric_type: str, value: dict) -> dict:
    """Validate value structure based on metric_type."""
    if metric_type == "weight":
        v = WeightValue.model_validate(value)
        return v.model_dump()
    if metric_type == "muscle_index":
        v = MuscleIndexValue.model_validate(value)
        return v.model_dump()
    raise ValueError(f"Unknown metric_type: '{metric_type}'. Allowed: {list(METRIC_TYPES)}")


class MetricCreate(BaseModel):
    metric_type: Literal["weight", "muscle_index"]
    date: str = Field(..., description="Date in YYYY-MM-DD format")
    value: dict = Field(..., description="Metric value. For weight: {kg: number}. For muscle_index: {index: number}")

    @model_validator(mode="after")
    def validate_value_for_type(self):
        validate_metric_value(self.metric_type, self.value)
        return self


class MetricUpdate(BaseModel):
    date: Optional[str] = Field(None, description="Date in YYYY-MM-DD format")
    value: Optional[dict] = Field(None, description="Metric value")


class MetricResponse(BaseModel):
    id: int
    user_id: int
    metric_type: str
    date: str
    value: dict
    created_at: str

    class Config:
        from_attributes = True
