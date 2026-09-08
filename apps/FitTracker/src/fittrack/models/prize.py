"""Prize model for drawing rewards."""

from pydantic import Field, field_validator

from fittrack.models.base import IdentifiedModel
from fittrack.models.enums import FulfillmentType


class Prize(IdentifiedModel):
    """Prize in a sweepstakes drawing."""

    drawing_id: str
    sponsor_id: str | None = None
    rank: int = Field(ge=1)  # 1st, 2nd, 3rd place, etc.
    name: str = Field(max_length=255)
    description: str | None = None
    value_usd: float | None = Field(default=None, ge=0)
    quantity: int = Field(default=1, ge=1)
    fulfillment_type: FulfillmentType
    image_url: str | None = Field(default=None, max_length=500)

    @field_validator("value_usd")
    @classmethod
    def validate_value(cls, v: float | None) -> float | None:
        """Ensure value is non-negative if provided."""
        if v is not None and v < 0:
            raise ValueError("value_usd must be non-negative")
        return v
