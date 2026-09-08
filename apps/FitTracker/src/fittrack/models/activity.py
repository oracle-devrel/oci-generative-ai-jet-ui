"""Activity model for fitness activities."""

from datetime import datetime
from typing import Any

from pydantic import Field

from fittrack.models.base import IdentifiedModel
from fittrack.models.enums import ActivityType, Intensity


class Activity(IdentifiedModel):
    """Normalized fitness activity from tracker."""

    user_id: str
    connection_id: str | None = None
    external_id: str | None = None  # ID from the tracker provider
    activity_type: ActivityType
    start_time: datetime
    end_time: datetime | None = None
    duration_minutes: int | None = Field(default=None, ge=0)
    intensity: Intensity | None = None
    metrics: dict[str, Any] | None = None  # steps, calories, heart_rate, etc.
    points_earned: int = Field(default=0, ge=0)
    processed: bool = False
