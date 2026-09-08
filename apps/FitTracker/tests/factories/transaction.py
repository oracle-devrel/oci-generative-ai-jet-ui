"""Transaction factory for test data generation."""

from typing import Any

from tests.factories.base import fake, generate_id, random_choice, utc_now

TRANSACTION_TYPES = ["earn", "spend", "adjust", "expire"]


def create_transaction(
    id: str | None = None,
    user_id: str | None = None,
    transaction_type: str | None = None,
    amount: int | None = None,
    balance_after: int | None = None,
    reference_type: str | None = None,
    reference_id: str | None = None,
    description: str | None = None,
    **kwargs,
) -> dict[str, Any]:
    """Create a transaction document for testing."""
    now = utc_now()

    if transaction_type is None:
        transaction_type = random_choice(TRANSACTION_TYPES)

    if amount is None:
        amount = fake.random_int(10, 500)

    if balance_after is None:
        balance_after = fake.random_int(0, 10000)

    return {
        "_id": id or generate_id(),
        "user_id": user_id or generate_id(),
        "transaction_type": transaction_type,
        "amount": amount,
        "balance_after": balance_after,
        "reference_type": reference_type,
        "reference_id": reference_id,
        "description": description or f"{transaction_type.title()} points",
        "created_at": now.isoformat() + "Z",
        "updated_at": now.isoformat() + "Z",
        **kwargs,
    }


def create_earn_transaction(
    user_id: str, amount: int, balance_after: int, **kwargs
) -> dict[str, Any]:
    """Create an earn transaction."""
    return create_transaction(
        user_id=user_id,
        transaction_type="earn",
        amount=amount,
        balance_after=balance_after,
        reference_type="activity",
        **kwargs,
    )


def create_spend_transaction(
    user_id: str, amount: int, balance_after: int, **kwargs
) -> dict[str, Any]:
    """Create a spend transaction."""
    return create_transaction(
        user_id=user_id,
        transaction_type="spend",
        amount=amount,
        balance_after=balance_after,
        reference_type="ticket_purchase",
        **kwargs,
    )
