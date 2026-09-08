"""Ticket model for sweepstakes entries."""

from fittrack.models.base import IdentifiedModel


class Ticket(IdentifiedModel):
    """Sweepstakes ticket (entry)."""

    drawing_id: str
    user_id: str
    ticket_number: int | None = None  # Assigned at drawing close
    purchase_transaction_id: str | None = None
    is_winner: bool = False
    prize_id: str | None = None  # Set if this ticket won a prize
