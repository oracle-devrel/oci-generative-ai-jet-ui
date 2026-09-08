"""User API schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from fittrack.models.enums import UserRole, UserStatus


class UserBase(BaseModel):
    """Base user fields."""

    email: EmailStr


class UserCreate(UserBase):
    """Schema for creating a user."""

    password: str = Field(min_length=12, description="Password (12+ characters)")


class UserUpdate(BaseModel):
    """Schema for updating a user."""

    email: EmailStr | None = None
    status: UserStatus | None = None
    role: UserRole | None = None


class UserResponse(BaseModel):
    """Schema for user response."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(alias="_id")
    email: EmailStr
    email_verified: bool
    email_verified_at: datetime | None = None
    status: UserStatus
    role: UserRole
    premium_expires_at: datetime | None = None
    point_balance: int
    last_login_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class UserSummary(BaseModel):
    """Minimal user info for embedding."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(alias="_id")
    email: EmailStr
    status: UserStatus
    role: UserRole
    point_balance: int


class UserListResponse(BaseModel):
    """Response for user list."""

    items: list[UserResponse]
    pagination: dict
