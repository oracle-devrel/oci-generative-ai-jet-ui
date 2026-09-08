"""Tracker connection API schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from fittrack.models.enums import Provider, SyncStatus


class ConnectionCreate(BaseModel):
    """Schema for creating a connection."""

    user_id: str
    provider: Provider
    is_primary: bool = False


class ConnectionResponse(BaseModel):
    """Schema for connection response."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(alias="_id")
    user_id: str
    provider: Provider
    is_primary: bool
    token_expires_at: datetime | None = None
    last_sync_at: datetime | None = None
    sync_status: SyncStatus
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime


class ConnectionSummary(BaseModel):
    """Minimal connection info for embedding."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(alias="_id")
    provider: Provider
    sync_status: SyncStatus
    last_sync_at: datetime | None = None
