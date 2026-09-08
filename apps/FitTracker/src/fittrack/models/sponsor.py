"""Sponsor model for prize providers."""

from pydantic import EmailStr, Field

from fittrack.models.base import IdentifiedModel
from fittrack.models.enums import SponsorStatus


class Sponsor(IdentifiedModel):
    """Prize sponsor company."""

    name: str = Field(max_length=255)
    contact_name: str | None = Field(default=None, max_length=255)
    contact_email: EmailStr | None = None
    contact_phone: str | None = Field(default=None, max_length=20)
    website_url: str | None = Field(default=None, max_length=500)
    logo_url: str | None = Field(default=None, max_length=500)
    status: SponsorStatus = SponsorStatus.ACTIVE
    notes: str | None = None
