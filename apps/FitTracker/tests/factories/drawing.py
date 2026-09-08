"""Drawing factory for test data generation."""

from datetime import datetime, timedelta
from typing import Any

from tests.factories.base import fake, generate_id, random_choice, utc_now

DRAWING_TYPES = ["daily", "weekly", "monthly", "annual"]
DRAWING_STATUSES = ["draft", "scheduled", "open", "closed", "completed", "cancelled"]

TICKET_COSTS = {
    "daily": 100,
    "weekly": 500,
    "monthly": 2000,
    "annual": 10000,
}


def create_drawing(
    id: str | None = None,
    drawing_type: str | None = None,
    name: str | None = None,
    description: str | None = None,
    ticket_cost_points: int | None = None,
    drawing_time: datetime | None = None,
    ticket_sales_close: datetime | None = None,
    eligibility: dict | None = None,
    status: str = "open",
    total_tickets: int = 0,
    random_seed: str | None = None,
    created_by: str | None = None,
    completed_at: datetime | None = None,
    **kwargs,
) -> dict[str, Any]:
    """Create a drawing document for testing."""
    now = utc_now()

    if drawing_type is None:
        drawing_type = random_choice(DRAWING_TYPES)

    if ticket_cost_points is None:
        ticket_cost_points = TICKET_COSTS.get(drawing_type, 100)

    if drawing_time is None:
        drawing_time = now + timedelta(days=1)

    if ticket_sales_close is None:
        ticket_sales_close = drawing_time - timedelta(hours=1)

    if name is None:
        name = f"{drawing_type.title()} Drawing - {fake.date()}"

    return {
        "_id": id or generate_id(),
        "drawing_type": drawing_type,
        "name": name,
        "description": description or f"Win prizes in this {drawing_type} drawing!",
        "ticket_cost_points": ticket_cost_points,
        "drawing_time": drawing_time.isoformat() + "Z",
        "ticket_sales_close": ticket_sales_close.isoformat() + "Z",
        "eligibility": eligibility,
        "status": status,
        "total_tickets": total_tickets,
        "random_seed": random_seed,
        "created_by": created_by,
        "completed_at": completed_at.isoformat() + "Z" if completed_at else None,
        "created_at": now.isoformat() + "Z",
        "updated_at": now.isoformat() + "Z",
        **kwargs,
    }


def create_open_drawing(**kwargs) -> dict[str, Any]:
    """Create an open drawing ready for ticket purchases."""
    return create_drawing(status="open", **kwargs)


def create_completed_drawing(**kwargs) -> dict[str, Any]:
    """Create a completed drawing."""
    now = utc_now()
    return create_drawing(
        status="completed",
        drawing_time=now - timedelta(days=1),
        ticket_sales_close=now - timedelta(days=1, hours=1),
        completed_at=now - timedelta(days=1),
        total_tickets=fake.random_int(100, 1000),
        random_seed=fake.sha256()[:16],
        **kwargs,
    )
