"""Point transaction model for the points ledger."""

from pydantic import Field, field_validator

from fittrack.models.base import IdentifiedModel
from fittrack.models.enums import TransactionType


class PointTransaction(IdentifiedModel):
    """Point transaction record."""

    user_id: str
    transaction_type: TransactionType
    amount: int = Field(gt=0)  # Always positive, type indicates direction
    balance_after: int = Field(ge=0)
    reference_type: str | None = None  # activity, ticket_purchase, admin_adjust
    reference_id: str | None = None
    description: str | None = Field(default=None, max_length=255)

    @field_validator("amount")
    @classmethod
    def validate_amount_positive(cls, v: int) -> int:
        """Ensure amount is positive."""
        if v <= 0:
            raise ValueError("amount must be positive")
        return v
