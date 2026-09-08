"""Profile API schemas."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from fittrack.models.enums import BiologicalSex, FitnessLevel


class ProfileBase(BaseModel):
    """Base profile fields."""

    display_name: str = Field(min_length=3, max_length=50)
    date_of_birth: date
    state_of_residence: str = Field(min_length=2, max_length=2)
    biological_sex: BiologicalSex
    fitness_level: FitnessLevel
    height_inches: int | None = Field(default=None, ge=36, le=96)
    weight_pounds: int | None = Field(default=None, ge=50, le=1000)
    goals: list[str] | None = None


class ProfileCreate(ProfileBase):
    """Schema for creating a profile."""

    user_id: str


class ProfileUpdate(BaseModel):
    """Schema for updating a profile."""

    display_name: str | None = Field(default=None, min_length=3, max_length=50)
    state_of_residence: str | None = Field(default=None, min_length=2, max_length=2)
    fitness_level: FitnessLevel | None = None
    height_inches: int | None = Field(default=None, ge=36, le=96)
    weight_pounds: int | None = Field(default=None, ge=50, le=1000)
    goals: list[str] | None = None


class ProfileResponse(BaseModel):
    """Schema for profile response."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(alias="_id")
    user_id: str
    display_name: str
    date_of_birth: date
    state_of_residence: str
    biological_sex: BiologicalSex
    fitness_level: FitnessLevel
    age_bracket: str | None
    tier_code: str | None
    height_inches: int | None
    weight_pounds: int | None
    goals: list[str] | None
    created_at: datetime
    updated_at: datetime


class ProfileSummary(BaseModel):
    """Minimal profile info for embedding."""

    model_config = ConfigDict(from_attributes=True)

    display_name: str
    tier_code: str | None
    fitness_level: FitnessLevel
