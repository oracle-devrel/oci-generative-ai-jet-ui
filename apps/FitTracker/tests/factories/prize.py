"""Prize factory for test data generation."""

from typing import Any

from tests.factories.base import generate_id, random_choice, utc_now

FULFILLMENT_TYPES = ["digital", "physical"]

PRIZE_TEMPLATES = [
    {"name": "Gift Card - $100", "value_usd": 100.0, "fulfillment_type": "digital"},
    {"name": "Gift Card - $50", "value_usd": 50.0, "fulfillment_type": "digital"},
    {"name": "Fitness Tracker", "value_usd": 150.0, "fulfillment_type": "physical"},
    {"name": "Wireless Earbuds", "value_usd": 80.0, "fulfillment_type": "physical"},
    {"name": "Gym Membership - 1 Month", "value_usd": 50.0, "fulfillment_type": "digital"},
    {"name": "Running Shoes", "value_usd": 120.0, "fulfillment_type": "physical"},
    {"name": "Yoga Mat", "value_usd": 30.0, "fulfillment_type": "physical"},
    {"name": "Water Bottle", "value_usd": 25.0, "fulfillment_type": "physical"},
]


def create_prize(
    id: str | None = None,
    drawing_id: str | None = None,
    sponsor_id: str | None = None,
    rank: int = 1,
    name: str | None = None,
    description: str | None = None,
    value_usd: float | None = None,
    quantity: int = 1,
    fulfillment_type: str | None = None,
    image_url: str | None = None,
    **kwargs,
) -> dict[str, Any]:
    """Create a prize document for testing."""
    now = utc_now()

    template = random_choice(PRIZE_TEMPLATES)

    return {
        "_id": id or generate_id(),
        "drawing_id": drawing_id or generate_id(),
        "sponsor_id": sponsor_id,
        "rank": rank,
        "name": name or template["name"],
        "description": description or f"Prize: {template['name']}",
        "value_usd": value_usd if value_usd is not None else template["value_usd"],
        "quantity": quantity,
        "fulfillment_type": fulfillment_type or template["fulfillment_type"],
        "image_url": image_url,
        "created_at": now.isoformat() + "Z",
        "updated_at": now.isoformat() + "Z",
        **kwargs,
    }


def create_prizes_for_drawing(drawing_id: str, count: int = 3) -> list[dict[str, Any]]:
    """Create a set of ranked prizes for a drawing."""
    prizes = []
    for rank in range(1, count + 1):
        template = PRIZE_TEMPLATES[(rank - 1) % len(PRIZE_TEMPLATES)]
        prizes.append(
            create_prize(
                drawing_id=drawing_id,
                rank=rank,
                name=template["name"],
                value_usd=template["value_usd"],
                fulfillment_type=template["fulfillment_type"],
            )
        )
    return prizes
