"""Fulfillment factory for test data generation."""

from datetime import datetime, timedelta
from typing import Any

from tests.factories.base import fake, generate_id, random_choice, utc_now

FULFILLMENT_STATUSES = [
    "pending",
    "winner_notified",
    "address_confirmed",
    "address_invalid",
    "shipped",
    "delivered",
    "forfeited",
]

CARRIERS = ["UPS", "FedEx", "USPS", "DHL"]


def create_fulfillment(
    id: str | None = None,
    ticket_id: str | None = None,
    prize_id: str | None = None,
    user_id: str | None = None,
    status: str = "pending",
    shipping_address: dict | None = None,
    tracking_number: str | None = None,
    carrier: str | None = None,
    notes: str | None = None,
    notified_at: datetime | None = None,
    address_confirmed_at: datetime | None = None,
    shipped_at: datetime | None = None,
    delivered_at: datetime | None = None,
    forfeit_at: datetime | None = None,
    **kwargs,
) -> dict[str, Any]:
    """Create a fulfillment document for testing."""
    now = utc_now()

    return {
        "_id": id or generate_id(),
        "ticket_id": ticket_id or generate_id(),
        "prize_id": prize_id or generate_id(),
        "user_id": user_id or generate_id(),
        "status": status,
        "shipping_address": shipping_address,
        "tracking_number": tracking_number,
        "carrier": carrier,
        "notes": notes,
        "notified_at": notified_at.isoformat() + "Z" if notified_at else None,
        "address_confirmed_at": address_confirmed_at.isoformat() + "Z"
        if address_confirmed_at
        else None,
        "shipped_at": shipped_at.isoformat() + "Z" if shipped_at else None,
        "delivered_at": delivered_at.isoformat() + "Z" if delivered_at else None,
        "forfeit_at": forfeit_at.isoformat() + "Z" if forfeit_at else None,
        "created_at": now.isoformat() + "Z",
        "updated_at": now.isoformat() + "Z",
        **kwargs,
    }


def create_shipping_address() -> dict[str, Any]:
    """Create a realistic US shipping address."""
    from tests.factories.profile import ELIGIBLE_STATES

    return {
        "name": fake.name(),
        "street1": fake.street_address(),
        "street2": fake.secondary_address() if fake.boolean(chance_of_getting_true=30) else None,
        "city": fake.city(),
        "state": random_choice(ELIGIBLE_STATES),
        "zip_code": fake.zipcode(),
        "country": "US",
        "phone": fake.phone_number(),
    }


def create_shipped_fulfillment(**kwargs) -> dict[str, Any]:
    """Create a fulfillment that has been shipped."""
    now = utc_now()
    return create_fulfillment(
        status="shipped",
        shipping_address=create_shipping_address(),
        tracking_number=f"1Z{fake.random_number(digits=16)}",
        carrier=random_choice(CARRIERS),
        notified_at=now - timedelta(days=7),
        address_confirmed_at=now - timedelta(days=5),
        shipped_at=now - timedelta(days=1),
        **kwargs,
    )


def create_delivered_fulfillment(**kwargs) -> dict[str, Any]:
    """Create a fulfillment that has been delivered."""
    now = utc_now()
    return create_fulfillment(
        status="delivered",
        shipping_address=create_shipping_address(),
        tracking_number=f"1Z{fake.random_number(digits=16)}",
        carrier=random_choice(CARRIERS),
        notified_at=now - timedelta(days=14),
        address_confirmed_at=now - timedelta(days=10),
        shipped_at=now - timedelta(days=5),
        delivered_at=now - timedelta(days=1),
        **kwargs,
    )
