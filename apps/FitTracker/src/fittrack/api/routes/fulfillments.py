"""Fulfillment API routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from fittrack.api.schemas.common import PaginationMeta
from fittrack.api.schemas.fulfillment import FulfillmentUpdate
from fittrack.models.base import utc_now
from fittrack.models.enums import FulfillmentStatus
from fittrack.repositories.fulfillment import FulfillmentRepository

router = APIRouter(prefix="/fulfillments", tags=["fulfillments"])


def get_fulfillment_repo() -> FulfillmentRepository:
    """Dependency to get fulfillment repository."""
    return FulfillmentRepository()


@router.get("")
def list_fulfillments(
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    status_filter: FulfillmentStatus | None = None,
    user_id: str | None = None,
    repo: FulfillmentRepository = Depends(get_fulfillment_repo),
) -> dict:
    """List fulfillments with pagination."""
    offset = (page - 1) * limit

    if status_filter:
        fulfillments = repo.find_by_status(status_filter, limit=limit, offset=offset)
        total = repo.count(
            "JSON_VALUE(data, '$.status') = :status",
            {"status": status_filter.value},
        )
    elif user_id:
        fulfillments = repo.find_by_user(user_id, limit=limit, offset=offset)
        total = repo.count(
            "JSON_VALUE(data, '$.user_id') = :user_id",
            {"user_id": user_id},
        )
    else:
        fulfillments = repo.find_all(limit=limit, offset=offset)
        total = repo.count()

    return {
        "items": fulfillments,
        "pagination": PaginationMeta.from_pagination(page, limit, total).model_dump(),
    }


@router.get("/pending-shipment")
def list_pending_shipment(
    repo: FulfillmentRepository = Depends(get_fulfillment_repo),
) -> list[dict]:
    """List fulfillments ready for shipment."""
    return repo.find_pending_shipment()


@router.get("/overdue")
def list_overdue(
    days: int = 30,
    repo: FulfillmentRepository = Depends(get_fulfillment_repo),
) -> list[dict]:
    """List overdue fulfillments."""
    return repo.find_overdue(days=days)


@router.get("/{fulfillment_id}")
def get_fulfillment(
    fulfillment_id: str,
    repo: FulfillmentRepository = Depends(get_fulfillment_repo),
) -> dict:
    """Get a fulfillment by ID."""
    fulfillment = repo.find_by_id(fulfillment_id)
    if not fulfillment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Fulfillment {fulfillment_id} not found",
        )
    return fulfillment


@router.put("/{fulfillment_id}")
def update_fulfillment(
    fulfillment_id: str,
    fulfillment_data: FulfillmentUpdate,
    repo: FulfillmentRepository = Depends(get_fulfillment_repo),
) -> dict:
    """Update a fulfillment."""
    fulfillment = repo.find_by_id(fulfillment_id)
    if not fulfillment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Fulfillment {fulfillment_id} not found",
        )

    # Validate status transitions
    current_status = fulfillment.get("status")
    new_status = fulfillment_data.status

    if new_status and current_status == "forfeited":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot update forfeited fulfillment",
        )

    # Handle shipping info update
    if fulfillment_data.tracking_number and fulfillment_data.carrier:
        repo.update_shipping_info(
            fulfillment_id,
            fulfillment_data.tracking_number,
            fulfillment_data.carrier,
        )
        fulfillment = repo.find_by_id(fulfillment_id)
        return fulfillment

    # Handle address update
    if fulfillment_data.shipping_address:
        repo.update_address(fulfillment_id, fulfillment_data.shipping_address)

    # Handle status update
    if new_status:
        repo.update_status(fulfillment_id, new_status)

    # Build update for other fields
    update_data = fulfillment_data.model_dump(
        exclude_unset=True,
        exclude={"status", "shipping_address", "tracking_number", "carrier"},
    )

    if update_data:
        # Convert enums
        updated_fulfillment = {**fulfillment, **update_data}
        updated_fulfillment["updated_at"] = utc_now().isoformat() + "Z"
        repo.update(fulfillment_id, updated_fulfillment)

    return repo.find_by_id(fulfillment_id)
