from pydantic import BaseModel, Field, field_validator, model_validator, EmailStr
from typing import Optional, Literal


class UserLogin(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6, max_length=72)
    email: EmailStr
    registration_code: Optional[str] = None

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
    email: Optional[str] = None

    class Config:
        from_attributes = True


class ProfileResponse(BaseModel):
    id: int
    username: str
    email: Optional[str] = None
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
    email: Optional[EmailStr] = None


class AdminUserResponse(BaseModel):
    id: int
    username: str
    email: Optional[str] = None
    is_admin: bool
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    age: Optional[int] = None
    height_cm: Optional[float] = None
    gender: Optional[str] = None

    class Config:
        from_attributes = True


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=6, max_length=72)

    @field_validator('new_password')
    @classmethod
    def validate_password_length(cls, v: str) -> str:
        if len(v.encode('utf-8')) > 72:
            raise ValueError('Password cannot exceed 72 bytes. Please use a shorter password.')
        return v


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

METRIC_TYPES = ("weight", "muscle_index", "body_measurements")

# Standard body circumference sites (fitness/ACE-style). All values in cm.
# Bilateral parts have _left_cm and _right_cm.
BODY_MEASUREMENT_SITES = (
    "neck_cm",
    "shoulder_cm",
    "chest_cm",
    "biceps_left_cm",
    "biceps_right_cm",
    "triceps_left_cm",
    "triceps_right_cm",
    "forearm_left_cm",
    "forearm_right_cm",
    "waist_cm",
    "abdomen_cm",
    "hips_cm",
    "thigh_left_cm",
    "thigh_right_cm",
    "calf_left_cm",
    "calf_right_cm",
)

# Value schemas per metric type (for validation)
class WeightValue(BaseModel):
    kg: float = Field(..., gt=0, description="Weight in kg")


class MuscleIndexValue(BaseModel):
    index: float = Field(..., ge=0, le=100, description="Muscle index (0-100)")


class BodyMeasurementsValue(BaseModel):
    """Body circumference measurements in cm. All fields optional; send only what you measured.
    Bilateral parts (arms, legs) use _left_cm and _right_cm."""

    model_config = {"extra": "forbid"}

    # Single (midline / full circumference)
    neck_cm: Optional[float] = Field(None, gt=0, le=250, description="Neck circumference (cm)")
    shoulder_cm: Optional[float] = Field(None, gt=0, le=250, description="Shoulder circumference (cm)")
    chest_cm: Optional[float] = Field(None, gt=0, le=250, description="Chest at nipple level (cm)")
    waist_cm: Optional[float] = Field(None, gt=0, le=250, description="Waist, narrowest above navel (cm)")
    abdomen_cm: Optional[float] = Field(None, gt=0, le=250, description="Abdomen at navel level (cm)")
    hips_cm: Optional[float] = Field(None, gt=0, le=250, description="Hips, maximal buttocks (cm)")
    # Left/right (bilateral)
    biceps_left_cm: Optional[float] = Field(None, gt=0, le=250, description="Biceps left (cm)")
    biceps_right_cm: Optional[float] = Field(None, gt=0, le=250, description="Biceps right (cm)")
    triceps_left_cm: Optional[float] = Field(None, gt=0, le=250, description="Triceps left (cm)")
    triceps_right_cm: Optional[float] = Field(None, gt=0, le=250, description="Triceps right (cm)")
    forearm_left_cm: Optional[float] = Field(None, gt=0, le=250, description="Forearm left (cm)")
    forearm_right_cm: Optional[float] = Field(None, gt=0, le=250, description="Forearm right (cm)")
    thigh_left_cm: Optional[float] = Field(None, gt=0, le=250, description="Thigh left (cm)")
    thigh_right_cm: Optional[float] = Field(None, gt=0, le=250, description="Thigh right (cm)")
    calf_left_cm: Optional[float] = Field(None, gt=0, le=250, description="Calf left (cm)")
    calf_right_cm: Optional[float] = Field(None, gt=0, le=250, description="Calf right (cm)")

    @model_validator(mode="after")
    def at_least_one_measurement(self):
        if all(v is None for v in self.model_dump().values()):
            raise ValueError("At least one body measurement (in cm) is required")
        return self


def validate_metric_value(metric_type: str, value: dict) -> dict:
    """Validate value structure based on metric_type."""
    if metric_type == "weight":
        v = WeightValue.model_validate(value)
        return v.model_dump()
    if metric_type == "muscle_index":
        v = MuscleIndexValue.model_validate(value)
        return v.model_dump()
    if metric_type == "body_measurements":
        v = BodyMeasurementsValue.model_validate(value)
        # Return only non-None fields so we don't store nulls
        return {k: w for k, w in v.model_dump().items() if w is not None}
    raise ValueError(f"Unknown metric_type: '{metric_type}'. Allowed: {list(METRIC_TYPES)}")


class MetricCreate(BaseModel):
    metric_type: Literal["weight", "muscle_index", "body_measurements"]
    date: str = Field(..., description="Date in YYYY-MM-DD format")
    value: dict = Field(
        ...,
        description="Metric value. weight: {kg}. muscle_index: {index}. body_measurements: single (neck_cm?, shoulder_cm?, chest_cm?, waist_cm?, abdomen_cm?, hips_cm?) and bilateral (biceps_left_cm?, biceps_right_cm?, triceps_left_cm?, triceps_right_cm?, forearm_left_cm?, forearm_right_cm?, thigh_left_cm?, thigh_right_cm?, calf_left_cm?, calf_right_cm?) in cm, at least one.",
    )

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
