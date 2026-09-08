"""Drawing API schemas."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from fittrack.models.enums import DrawingStatus, DrawingType


class DrawingCreate(BaseModel):
    """Schema for creating a drawing."""

    drawing_type: DrawingType
    name: str = Field(max_length=255)
    description: str | None = None
    ticket_cost_points: int = Field(gt=0)
    drawing_time: datetime
    ticket_sales_close: datetime
    eligibility: dict[str, Any] | None = None
    status: DrawingStatus = DrawingStatus.DRAFT


class DrawingUpdate(BaseModel):
    """Schema for updating a drawing."""

    name: str | None = Field(default=None, max_length=255)
    description: str | None = None
    ticket_cost_points: int | None = Field(default=None, gt=0)
    drawing_time: datetime | None = None
    ticket_sales_close: datetime | None = None
    eligibility: dict[str, Any] | None = None
    status: DrawingStatus | None = None


class DrawingResponse(BaseModel):
    """Schema for drawing response."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(alias="_id")
    drawing_type: DrawingType
    name: str
    description: str | None
    ticket_cost_points: int
    drawing_time: datetime
    ticket_sales_close: datetime
    eligibility: dict[str, Any] | None
    status: DrawingStatus
    total_tickets: int
    random_seed: str | None
    created_by: str | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class DrawingSummary(BaseModel):
    """Minimal drawing info for lists."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(alias="_id")
    drawing_type: DrawingType
    name: str
    ticket_cost_points: int
    drawing_time: datetime
    status: DrawingStatus
    total_tickets: int
