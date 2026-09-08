"""Drawing model for sweepstakes."""

from datetime import datetime
from typing import Any

from pydantic import Field, field_validator

from fittrack.models.base import IdentifiedModel
from fittrack.models.enums import DrawingStatus, DrawingType


class Drawing(IdentifiedModel):
    """Sweepstakes drawing."""

    drawing_type: DrawingType
    name: str = Field(max_length=255)
    description: str | None = None
    ticket_cost_points: int = Field(gt=0)
    drawing_time: datetime
    ticket_sales_close: datetime
    eligibility: dict[str, Any] | None = None  # {"user_type": "all", "min_account_age_days": 7}
    status: DrawingStatus = DrawingStatus.DRAFT
    total_tickets: int = Field(default=0, ge=0)
    random_seed: str | None = None  # For audit trail
    created_by: str | None = None
    completed_at: datetime | None = None

    @field_validator("ticket_cost_points")
    @classmethod
    def validate_ticket_cost(cls, v: int) -> int:
        """Ensure ticket cost is positive."""
        if v <= 0:
            raise ValueError("ticket_cost_points must be positive")
        return v
