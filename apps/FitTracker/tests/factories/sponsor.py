"""Sponsor factory for test data generation."""

from typing import Any

from tests.factories.base import fake, generate_id, random_choice, utc_now

SPONSOR_STATUSES = ["active", "inactive"]

SPONSOR_NAMES = [
    "FitGear Pro",
    "HealthyLife Supplements",
    "ActiveWear Co.",
    "Energy Drinks Inc.",
    "Sports Equipment Direct",
    "Wellness First",
    "Athletic Performance Labs",
    "Outdoor Adventure Gear",
    "Nutrition Plus",
    "Fitness Tech Solutions",
]


def create_sponsor(
    id: str | None = None,
    name: str | None = None,
    contact_name: str | None = None,
    contact_email: str | None = None,
    contact_phone: str | None = None,
    website_url: str | None = None,
    logo_url: str | None = None,
    status: str = "active",
    notes: str | None = None,
    **kwargs,
) -> dict[str, Any]:
    """Create a sponsor document for testing."""
    now = utc_now()

    if name is None:
        name = random_choice(SPONSOR_NAMES) + f" {fake.random_number(digits=3)}"

    return {
        "_id": id or generate_id(),
        "name": name,
        "contact_name": contact_name or fake.name(),
        "contact_email": contact_email or fake.company_email(),
        "contact_phone": contact_phone or fake.phone_number(),
        "website_url": website_url or f"https://{fake.domain_name()}",
        "logo_url": logo_url or f"https://example.com/logos/{generate_id()[:8]}.png",
        "status": status,
        "notes": notes,
        "created_at": now.isoformat() + "Z",
        "updated_at": now.isoformat() + "Z",
        **kwargs,
    }


def create_active_sponsor(**kwargs) -> dict[str, Any]:
    """Create an active sponsor."""
    return create_sponsor(status="active", **kwargs)


def create_sponsors(count: int) -> list[dict[str, Any]]:
    """Create multiple sponsor documents."""
    sponsors = []
    for i in range(count):
        name = SPONSOR_NAMES[i % len(SPONSOR_NAMES)]
        if i >= len(SPONSOR_NAMES):
            name += f" #{i}"
        sponsors.append(create_sponsor(name=name))
    return sponsors
