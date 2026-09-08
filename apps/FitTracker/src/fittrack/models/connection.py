"""Tracker connection model for fitness API integrations."""

from datetime import datetime

from pydantic import Field

from fittrack.models.base import IdentifiedModel
from fittrack.models.enums import Provider, SyncStatus


class TrackerConnection(IdentifiedModel):
    """OAuth connection to a fitness tracker provider."""

    user_id: str
    provider: Provider
    is_primary: bool = False
    access_token: str | None = None  # Encrypted before storage
    refresh_token: str | None = None  # Encrypted before storage
    token_expires_at: datetime | None = None
    last_sync_at: datetime | None = None
    sync_status: SyncStatus = SyncStatus.PENDING
    error_message: str | None = Field(default=None, max_length=500)
