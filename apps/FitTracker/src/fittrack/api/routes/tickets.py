"""Ticket API routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from fittrack.api.schemas.common import PaginationMeta
from fittrack.api.schemas.ticket import TicketCreate
from fittrack.models.base import generate_uuid, utc_now
from fittrack.repositories.drawing import DrawingRepository
from fittrack.repositories.ticket import TicketRepository

router = APIRouter(prefix="/tickets", tags=["tickets"])


def get_ticket_repo() -> TicketRepository:
    """Dependency to get ticket repository."""
    return TicketRepository()


def get_drawing_repo() -> DrawingRepository:
    """Dependency to get drawing repository."""
    return DrawingRepository()


@router.get("")
def list_tickets(
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    user_id: str | None = None,
    drawing_id: str | None = None,
    repo: TicketRepository = Depends(get_ticket_repo),
) -> dict:
    """List tickets with pagination."""
    offset = (page - 1) * limit

    if user_id and drawing_id:
        tickets = repo.find_by_user_and_drawing(user_id, drawing_id)
        total = len(tickets)
        tickets = tickets[offset : offset + limit]
    elif user_id:
        tickets = repo.find_by_user(user_id, limit=limit, offset=offset)
        total = repo.count(
            "JSON_VALUE(data, '$.user_id') = :user_id",
            {"user_id": user_id},
        )
    elif drawing_id:
        tickets = repo.find_by_drawing(drawing_id, limit=limit, offset=offset)
        total = repo.count_by_drawing(drawing_id)
    else:
        tickets = repo.find_all(limit=limit, offset=offset)
        total = repo.count()

    return {
        "items": tickets,
        "pagination": PaginationMeta.from_pagination(page, limit, total).model_dump(),
    }


@router.get("/{ticket_id}")
def get_ticket(
    ticket_id: str,
    repo: TicketRepository = Depends(get_ticket_repo),
) -> dict:
    """Get a ticket by ID."""
    ticket = repo.find_by_id(ticket_id)
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket {ticket_id} not found",
        )
    return ticket


@router.post("", status_code=status.HTTP_201_CREATED)
def create_ticket(
    ticket_data: TicketCreate,
    repo: TicketRepository = Depends(get_ticket_repo),
    drawing_repo: DrawingRepository = Depends(get_drawing_repo),
) -> dict:
    """Create tickets (purchase entry)."""
    # Get drawing
    drawing = drawing_repo.find_by_id(ticket_data.drawing_id)
    if not drawing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Drawing {ticket_data.drawing_id} not found",
        )

    # Check drawing is open
    if drawing.get("status") != "open":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Drawing is not open for ticket sales",
        )

    # Create ticket document
    now = utc_now()
    ticket_doc = {
        "_id": generate_uuid(),
        "drawing_id": ticket_data.drawing_id,
        "user_id": "temp-user",  # Will come from auth in CP2
        "ticket_number": None,  # Assigned at drawing close
        "purchase_transaction_id": None,  # Set when points are deducted
        "is_winner": False,
        "prize_id": None,
        "created_at": now.isoformat() + "Z",
        "updated_at": now.isoformat() + "Z",
    }

    # Create requested quantity of tickets
    tickets = []
    for _ in range(ticket_data.quantity):
        ticket = {**ticket_doc, "_id": generate_uuid()}
        created = repo.create(ticket)
        tickets.append(created)

    # Increment drawing ticket count
    drawing_repo.increment_ticket_count(ticket_data.drawing_id, ticket_data.quantity)

    return {
        "tickets": tickets,
        "quantity": len(tickets),
        "drawing_id": ticket_data.drawing_id,
    }
