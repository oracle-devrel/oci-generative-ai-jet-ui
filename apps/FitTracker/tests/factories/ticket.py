"""Ticket factory for test data generation."""

from typing import Any

from tests.factories.base import fake, generate_id, utc_now


def create_ticket(
    id: str | None = None,
    drawing_id: str | None = None,
    user_id: str | None = None,
    ticket_number: int | None = None,
    purchase_transaction_id: str | None = None,
    is_winner: bool = False,
    prize_id: str | None = None,
    **kwargs,
) -> dict[str, Any]:
    """Create a ticket document for testing."""
    now = utc_now()

    return {
        "_id": id or generate_id(),
        "drawing_id": drawing_id or generate_id(),
        "user_id": user_id or generate_id(),
        "ticket_number": ticket_number,
        "purchase_transaction_id": purchase_transaction_id,
        "is_winner": is_winner,
        "prize_id": prize_id,
        "created_at": now.isoformat() + "Z",
        "updated_at": now.isoformat() + "Z",
        **kwargs,
    }


def create_winning_ticket(drawing_id: str, user_id: str, prize_id: str, **kwargs) -> dict[str, Any]:
    """Create a winning ticket."""
    return create_ticket(
        drawing_id=drawing_id,
        user_id=user_id,
        is_winner=True,
        prize_id=prize_id,
        ticket_number=fake.random_int(1, 1000),
        **kwargs,
    )


def create_tickets_for_drawing(
    drawing_id: str,
    count: int,
    user_ids: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Create multiple tickets for a drawing."""
    tickets = []
    for i in range(count):
        user_id = user_ids[i % len(user_ids)] if user_ids else generate_id()
        tickets.append(
            create_ticket(
                drawing_id=drawing_id,
                user_id=user_id,
                ticket_number=i + 1,
            )
        )
    return tickets
