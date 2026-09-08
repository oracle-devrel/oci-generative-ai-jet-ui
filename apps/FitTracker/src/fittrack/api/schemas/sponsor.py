"""Sponsor API schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from fittrack.models.enums import SponsorStatus


class SponsorCreate(BaseModel):
    """Schema for creating a sponsor."""

    name: str = Field(max_length=255)
    contact_name: str | None = Field(default=None, max_length=255)
    contact_email: EmailStr | None = None
    contact_phone: str | None = Field(default=None, max_length=20)
    website_url: str | None = Field(default=None, max_length=500)
    logo_url: str | None = Field(default=None, max_length=500)
    status: SponsorStatus = SponsorStatus.ACTIVE
    notes: str | None = None


class SponsorUpdate(BaseModel):
    """Schema for updating a sponsor."""

    name: str | None = Field(default=None, max_length=255)
    contact_name: str | None = Field(default=None, max_length=255)
    contact_email: EmailStr | None = None
    contact_phone: str | None = Field(default=None, max_length=20)
    website_url: str | None = Field(default=None, max_length=500)
    logo_url: str | None = Field(default=None, max_length=500)
    status: SponsorStatus | None = None
    notes: str | None = None


class SponsorResponse(BaseModel):
    """Schema for sponsor response."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(alias="_id")
    name: str
    contact_name: str | None
    contact_email: str | None
    contact_phone: str | None
    website_url: str | None
    logo_url: str | None
    status: SponsorStatus
    notes: str | None
    created_at: datetime
    updated_at: datetime


class SponsorSummary(BaseModel):
    """Minimal sponsor info for lists."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(alias="_id")
    name: str
    logo_url: str | None
    status: SponsorStatus
