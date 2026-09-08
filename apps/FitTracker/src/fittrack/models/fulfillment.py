"""Prize fulfillment model for delivery tracking."""

from datetime import datetime
from typing import Any

from pydantic import Field

from fittrack.models.base import IdentifiedModel
from fittrack.models.enums import FulfillmentStatus


class PrizeFulfillment(IdentifiedModel):
    """Prize fulfillment tracking record."""

    ticket_id: str
    prize_id: str
    user_id: str
    status: FulfillmentStatus = FulfillmentStatus.PENDING
    shipping_address: dict[str, Any] | None = None
    tracking_number: str | None = Field(default=None, max_length=100)
    carrier: str | None = Field(default=None, max_length=50)
    notes: str | None = None
    notified_at: datetime | None = None
    address_confirmed_at: datetime | None = None
    shipped_at: datetime | None = None
    delivered_at: datetime | None = None
    forfeit_at: datetime | None = None
