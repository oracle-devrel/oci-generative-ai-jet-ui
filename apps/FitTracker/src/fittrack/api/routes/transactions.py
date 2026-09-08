"""Point transaction API routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from fittrack.api.schemas.common import PaginationMeta
from fittrack.api.schemas.transaction import TransactionCreate
from fittrack.models.base import generate_uuid, utc_now
from fittrack.repositories.transaction import TransactionRepository
from fittrack.repositories.user import UserRepository

router = APIRouter(prefix="/transactions", tags=["transactions"])


def get_transaction_repo() -> TransactionRepository:
    """Dependency to get transaction repository."""
    return TransactionRepository()


def get_user_repo() -> UserRepository:
    """Dependency to get user repository."""
    return UserRepository()


@router.get("")
def list_transactions(
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    user_id: str | None = None,
    repo: TransactionRepository = Depends(get_transaction_repo),
) -> dict:
    """List transactions with pagination."""
    offset = (page - 1) * limit

    if user_id:
        transactions = repo.find_by_user(user_id, limit=limit, offset=offset)
        total = repo.count(
            "JSON_VALUE(data, '$.user_id') = :user_id",
            {"user_id": user_id},
        )
    else:
        transactions = repo.find_all(limit=limit, offset=offset)
        total = repo.count()

    return {
        "items": transactions,
        "pagination": PaginationMeta.from_pagination(page, limit, total).model_dump(),
    }


@router.get("/{transaction_id}")
def get_transaction(
    transaction_id: str,
    repo: TransactionRepository = Depends(get_transaction_repo),
) -> dict:
    """Get a transaction by ID."""
    transaction = repo.find_by_id(transaction_id)
    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaction {transaction_id} not found",
        )
    return transaction


@router.post("", status_code=status.HTTP_201_CREATED)
def create_transaction(
    transaction_data: TransactionCreate,
    repo: TransactionRepository = Depends(get_transaction_repo),
    user_repo: UserRepository = Depends(get_user_repo),
) -> dict:
    """Create a new transaction (admin only)."""
    # Get user to verify exists and get current balance
    user = user_repo.find_by_id(transaction_data.user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {transaction_data.user_id} not found",
        )

    current_balance = user.get("point_balance", 0)

    # Calculate new balance
    if transaction_data.transaction_type.value in ("earn", "adjust"):
        new_balance = current_balance + transaction_data.amount
    else:  # spend, expire
        new_balance = current_balance - transaction_data.amount

    if new_balance < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Insufficient balance. Current: {current_balance}, Required: {transaction_data.amount}",
        )

    # Create transaction document
    now = utc_now()
    transaction_doc = {
        "_id": generate_uuid(),
        "user_id": transaction_data.user_id,
        "transaction_type": transaction_data.transaction_type.value,
        "amount": transaction_data.amount,
        "balance_after": new_balance,
        "reference_type": transaction_data.reference_type,
        "reference_id": transaction_data.reference_id,
        "description": transaction_data.description,
        "created_at": now.isoformat() + "Z",
        "updated_at": now.isoformat() + "Z",
    }

    created = repo.create(transaction_doc)

    # Update user balance with optimistic locking
    version = user.get("version", 1)
    if not user_repo.update_point_balance(transaction_data.user_id, new_balance, version):
        # Rollback transaction
        repo.delete(created["_id"])
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Balance was modified concurrently. Please retry.",
        )

    return created
