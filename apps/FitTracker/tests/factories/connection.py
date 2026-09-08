"""Connection factory for test data generation."""

from datetime import datetime, timedelta
from typing import Any

from tests.factories.base import fake, generate_id, random_choice, random_datetime, utc_now

PROVIDERS = ["apple_health", "google_fit", "fitbit"]
SYNC_STATUSES = ["pending", "syncing", "success", "error"]


def create_connection(
    id: str | None = None,
    user_id: str | None = None,
    provider: str | None = None,
    is_primary: bool = False,
    access_token: str | None = None,
    refresh_token: str | None = None,
    token_expires_at: datetime | None = None,
    last_sync_at: datetime | None = None,
    sync_status: str = "success",
    error_message: str | None = None,
    **kwargs,
) -> dict[str, Any]:
    """Create a connection document for testing."""
    now = utc_now()

    if token_expires_at is None:
        token_expires_at = now + timedelta(hours=1)

    if last_sync_at is None and sync_status == "success":
        last_sync_at = random_datetime(start=now - timedelta(hours=1), end=now)

    return {
        "_id": id or generate_id(),
        "user_id": user_id or generate_id(),
        "provider": provider or random_choice(PROVIDERS),
        "is_primary": is_primary,
        "access_token": access_token or f"access_{fake.sha256()[:32]}",
        "refresh_token": refresh_token or f"refresh_{fake.sha256()[:32]}",
        "token_expires_at": token_expires_at.isoformat() + "Z" if token_expires_at else None,
        "last_sync_at": last_sync_at.isoformat() + "Z" if last_sync_at else None,
        "sync_status": sync_status,
        "error_message": error_message,
        "created_at": now.isoformat() + "Z",
        "updated_at": now.isoformat() + "Z",
        **kwargs,
    }


def create_connections_for_user(
    user_id: str, providers: list[str] | None = None
) -> list[dict[str, Any]]:
    """Create connections for a user with specified providers."""
    if providers is None:
        providers = [random_choice(PROVIDERS)]

    connections = []
    for i, provider in enumerate(providers):
        connections.append(
            create_connection(
                user_id=user_id,
                provider=provider,
                is_primary=(i == 0),
            )
        )
    return connections
