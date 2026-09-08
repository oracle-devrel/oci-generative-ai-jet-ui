"""Fulfillment API schemas."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from fittrack.models.enums import FulfillmentStatus


class FulfillmentUpdate(BaseModel):
    """Schema for updating a fulfillment."""

    status: FulfillmentStatus | None = None
    shipping_address: dict[str, Any] | None = None
    tracking_number: str | None = Field(default=None, max_length=100)
    carrier: str | None = Field(default=None, max_length=50)
    notes: str | None = None


class FulfillmentResponse(BaseModel):
    """Schema for fulfillment response."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(alias="_id")
    ticket_id: str
    prize_id: str
    user_id: str
    status: FulfillmentStatus
    shipping_address: dict[str, Any] | None
    tracking_number: str | None
    carrier: str | None
    notes: str | None
    notified_at: datetime | None
    address_confirmed_at: datetime | None
    shipped_at: datetime | None
    delivered_at: datetime | None
    forfeit_at: datetime | None
    created_at: datetime
    updated_at: datetime


class FulfillmentSummary(BaseModel):
    """Minimal fulfillment info for lists."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(alias="_id")
    status: FulfillmentStatus
    tracking_number: str | None
    carrier: str | None


class ShippingAddress(BaseModel):
    """Shipping address structure."""

    name: str
    street1: str
    street2: str | None = None
    city: str
    state: str = Field(min_length=2, max_length=2)
    zip_code: str
    country: str = "US"
    phone: str | None = None
