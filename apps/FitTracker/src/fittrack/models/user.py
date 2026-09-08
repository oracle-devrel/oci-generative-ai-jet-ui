"""User model for FitTrack accounts."""

from datetime import datetime

from pydantic import EmailStr, Field, field_validator

from fittrack.models.base import IdentifiedModel
from fittrack.models.enums import UserRole, UserStatus


class User(IdentifiedModel):
    """User account model."""

    email: EmailStr
    password_hash: str
    email_verified: bool = False
    email_verified_at: datetime | None = None
    status: UserStatus = UserStatus.PENDING
    role: UserRole = UserRole.USER
    premium_expires_at: datetime | None = None
    point_balance: int = Field(default=0, ge=0)
    last_login_at: datetime | None = None

    @field_validator("point_balance")
    @classmethod
    def validate_point_balance(cls, v: int) -> int:
        """Ensure point balance is non-negative."""
        if v < 0:
            raise ValueError("point_balance must be non-negative")
        return v
