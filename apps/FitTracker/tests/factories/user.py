"""User factory for test data generation."""

from datetime import datetime
from typing import Any

from tests.factories.base import fake, generate_id, utc_now


def create_user(
    id: str | None = None,
    email: str | None = None,
    password_hash: str | None = None,
    email_verified: bool = False,
    email_verified_at: datetime | None = None,
    status: str = "active",
    role: str = "user",
    premium_expires_at: datetime | None = None,
    point_balance: int | None = None,
    last_login_at: datetime | None = None,
    version: int = 1,
    **kwargs,
) -> dict[str, Any]:
    """Create a user document for testing.

    Args:
        id: User ID (generated if not provided).
        email: Email address.
        password_hash: Hashed password.
        email_verified: Whether email is verified.
        email_verified_at: When email was verified.
        status: User status (pending, active, suspended, banned).
        role: User role (user, premium, admin).
        premium_expires_at: Premium expiration time.
        point_balance: Current point balance.
        last_login_at: Last login timestamp.
        version: Optimistic locking version.

    Returns:
        User document dictionary.
    """
    now = utc_now()

    if point_balance is None:
        point_balance = fake.random_int(min=0, max=10000)

    return {
        "_id": id or generate_id(),
        "email": email or fake.unique.email(),
        "password_hash": password_hash or f"hash${fake.sha256()}",
        "email_verified": email_verified,
        "email_verified_at": email_verified_at.isoformat() + "Z" if email_verified_at else None,
        "status": status,
        "role": role,
        "premium_expires_at": premium_expires_at.isoformat() + "Z" if premium_expires_at else None,
        "point_balance": point_balance,
        "last_login_at": last_login_at.isoformat() + "Z" if last_login_at else None,
        "created_at": now.isoformat() + "Z",
        "updated_at": now.isoformat() + "Z",
        "version": version,
        **kwargs,
    }


def create_admin_user(**kwargs) -> dict[str, Any]:
    """Create an admin user."""
    return create_user(
        role="admin",
        email_verified=True,
        status="active",
        **kwargs,
    )


def create_premium_user(**kwargs) -> dict[str, Any]:
    """Create a premium user."""
    from datetime import timedelta

    return create_user(
        role="premium",
        email_verified=True,
        status="active",
        premium_expires_at=utc_now() + timedelta(days=365),
        **kwargs,
    )


def create_users(count: int, **kwargs) -> list[dict[str, Any]]:
    """Create multiple user documents."""
    return [create_user(**kwargs) for _ in range(count)]
