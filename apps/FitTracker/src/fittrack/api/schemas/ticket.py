"""Ticket API schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TicketCreate(BaseModel):
    """Schema for creating/purchasing tickets."""

    drawing_id: str
    quantity: int = Field(default=1, ge=1, le=100)


class TicketResponse(BaseModel):
    """Schema for ticket response."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(alias="_id")
    drawing_id: str
    user_id: str
    ticket_number: int | None
    purchase_transaction_id: str | None
    is_winner: bool
    prize_id: str | None
    created_at: datetime
    updated_at: datetime


class TicketSummary(BaseModel):
    """Minimal ticket info."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(alias="_id")
    ticket_number: int | None
    is_winner: bool
    created_at: datetime


class TicketPurchaseResponse(BaseModel):
    """Response for ticket purchase."""

    tickets: list[TicketResponse]
    quantity: int
    total_cost: int
    new_balance: int
