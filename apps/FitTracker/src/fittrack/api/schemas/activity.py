"""Activity API schemas."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from fittrack.models.enums import ActivityType, Intensity


class ActivityCreate(BaseModel):
    """Schema for creating an activity."""

    user_id: str
    connection_id: str | None = None
    external_id: str | None = None
    activity_type: ActivityType
    start_time: datetime
    end_time: datetime | None = None
    duration_minutes: int | None = Field(default=None, ge=0)
    intensity: Intensity | None = None
    metrics: dict[str, Any] | None = None


class ActivityResponse(BaseModel):
    """Schema for activity response."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(alias="_id")
    user_id: str
    connection_id: str | None
    external_id: str | None
    activity_type: ActivityType
    start_time: datetime
    end_time: datetime | None
    duration_minutes: int | None
    intensity: Intensity | None
    metrics: dict[str, Any] | None
    points_earned: int
    processed: bool
    created_at: datetime
    updated_at: datetime


class ActivitySummary(BaseModel):
    """Daily activity summary."""

    date: datetime
    total_steps: int = 0
    total_active_minutes: int = 0
    workout_count: int = 0
    total_points: int = 0


class ActivityDateRangeQuery(BaseModel):
    """Query parameters for activity date range."""

    start_date: datetime
    end_date: datetime
