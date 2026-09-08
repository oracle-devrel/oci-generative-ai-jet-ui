"""Point transaction API schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from fittrack.models.enums import TransactionType


class TransactionCreate(BaseModel):
    """Schema for creating a transaction (admin only)."""

    user_id: str
    transaction_type: TransactionType
    amount: int = Field(gt=0)
    reference_type: str | None = None
    reference_id: str | None = None
    description: str | None = Field(default=None, max_length=255)


class TransactionResponse(BaseModel):
    """Schema for transaction response."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(alias="_id")
    user_id: str
    transaction_type: TransactionType
    amount: int
    balance_after: int
    reference_type: str | None
    reference_id: str | None
    description: str | None
    created_at: datetime
    updated_at: datetime


class TransactionSummary(BaseModel):
    """Transaction summary for a period."""

    total_earned: int = 0
    total_spent: int = 0
    net_change: int = 0
    transaction_count: int = 0
