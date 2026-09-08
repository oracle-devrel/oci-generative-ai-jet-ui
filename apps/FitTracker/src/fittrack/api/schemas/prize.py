"""Prize API schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from fittrack.models.enums import FulfillmentType


class PrizeCreate(BaseModel):
    """Schema for creating a prize."""

    drawing_id: str
    sponsor_id: str | None = None
    rank: int = Field(ge=1)
    name: str = Field(max_length=255)
    description: str | None = None
    value_usd: float | None = Field(default=None, ge=0)
    quantity: int = Field(default=1, ge=1)
    fulfillment_type: FulfillmentType
    image_url: str | None = Field(default=None, max_length=500)


class PrizeUpdate(BaseModel):
    """Schema for updating a prize."""

    sponsor_id: str | None = None
    rank: int | None = Field(default=None, ge=1)
    name: str | None = Field(default=None, max_length=255)
    description: str | None = None
    value_usd: float | None = Field(default=None, ge=0)
    quantity: int | None = Field(default=None, ge=1)
    fulfillment_type: FulfillmentType | None = None
    image_url: str | None = Field(default=None, max_length=500)


class PrizeResponse(BaseModel):
    """Schema for prize response."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(alias="_id")
    drawing_id: str
    sponsor_id: str | None
    rank: int
    name: str
    description: str | None
    value_usd: float | None
    quantity: int
    fulfillment_type: FulfillmentType
    image_url: str | None
    created_at: datetime
    updated_at: datetime


class PrizeSummary(BaseModel):
    """Minimal prize info for lists."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(alias="_id")
    rank: int
    name: str
    value_usd: float | None
    fulfillment_type: FulfillmentType
