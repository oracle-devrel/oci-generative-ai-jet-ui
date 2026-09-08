"""Base model with common fields."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


def generate_uuid() -> str:
    """Generate a new UUID string."""
    return str(uuid.uuid4())


def utc_now() -> datetime:
    """Get current UTC datetime."""
    return datetime.utcnow()


class FitTrackModel(BaseModel):
    """Base model with common configuration."""

    model_config = ConfigDict(
        populate_by_name=True,
        str_strip_whitespace=True,
        validate_assignment=True,
        use_enum_values=True,
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert model to dictionary."""
        return self.model_dump(exclude_none=True)

    def to_json_dict(self) -> dict[str, Any]:
        """Convert model to JSON-serializable dictionary."""
        return self.model_dump(mode="json", exclude_none=True)


class TimestampMixin(BaseModel):
    """Mixin for timestamp fields."""

    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class IdentifiedModel(FitTrackModel, TimestampMixin):
    """Base model with ID and timestamps."""

    id: str = Field(default_factory=generate_uuid, alias="_id")
