"""Prize API routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from fittrack.api.schemas.common import PaginationMeta
from fittrack.api.schemas.prize import PrizeCreate, PrizeUpdate
from fittrack.models.base import generate_uuid, utc_now
from fittrack.repositories.drawing import DrawingRepository
from fittrack.repositories.prize import PrizeRepository

router = APIRouter(prefix="/prizes", tags=["prizes"])


def get_prize_repo() -> PrizeRepository:
    """Dependency to get prize repository."""
    return PrizeRepository()


def get_drawing_repo() -> DrawingRepository:
    """Dependency to get drawing repository."""
    return DrawingRepository()


@router.get("")
def list_prizes(
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    drawing_id: str | None = None,
    repo: PrizeRepository = Depends(get_prize_repo),
) -> dict:
    """List prizes with pagination."""
    offset = (page - 1) * limit

    if drawing_id:
        prizes = repo.find_by_drawing(drawing_id, limit=limit, offset=offset)
        total = repo.count_by_drawing(drawing_id)
    else:
        prizes = repo.find_all(limit=limit, offset=offset)
        total = repo.count()

    return {
        "items": prizes,
        "pagination": PaginationMeta.from_pagination(page, limit, total).model_dump(),
    }


@router.get("/{prize_id}")
def get_prize(
    prize_id: str,
    repo: PrizeRepository = Depends(get_prize_repo),
) -> dict:
    """Get a prize by ID."""
    prize = repo.find_by_id(prize_id)
    if not prize:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prize {prize_id} not found",
        )
    return prize


@router.post("", status_code=status.HTTP_201_CREATED)
def create_prize(
    prize_data: PrizeCreate,
    repo: PrizeRepository = Depends(get_prize_repo),
    drawing_repo: DrawingRepository = Depends(get_drawing_repo),
) -> dict:
    """Create a new prize."""
    # Verify drawing exists
    drawing = drawing_repo.find_by_id(prize_data.drawing_id)
    if not drawing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Drawing {prize_data.drawing_id} not found",
        )

    # Check drawing is not completed
    if drawing.get("status") in ("completed", "cancelled"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot add prizes to completed or cancelled drawings",
        )

    # Create prize document
    now = utc_now()
    prize_doc = {
        "_id": generate_uuid(),
        "drawing_id": prize_data.drawing_id,
        "sponsor_id": prize_data.sponsor_id,
        "rank": prize_data.rank,
        "name": prize_data.name,
        "description": prize_data.description,
        "value_usd": prize_data.value_usd,
        "quantity": prize_data.quantity,
        "fulfillment_type": prize_data.fulfillment_type.value,
        "image_url": prize_data.image_url,
        "created_at": now.isoformat() + "Z",
        "updated_at": now.isoformat() + "Z",
    }

    created = repo.create(prize_doc)
    return created


@router.put("/{prize_id}")
def update_prize(
    prize_id: str,
    prize_data: PrizeUpdate,
    repo: PrizeRepository = Depends(get_prize_repo),
) -> dict:
    """Update a prize."""
    prize = repo.find_by_id(prize_id)
    if not prize:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prize {prize_id} not found",
        )

    # Build update document
    update_data = prize_data.model_dump(exclude_unset=True)
    if not update_data:
        return prize

    # Convert enums to values
    if "fulfillment_type" in update_data and update_data["fulfillment_type"]:
        update_data["fulfillment_type"] = update_data["fulfillment_type"].value

    # Merge updates into existing prize
    updated_prize = {**prize, **update_data}
    updated_prize["updated_at"] = utc_now().isoformat() + "Z"

    repo.update(prize_id, updated_prize)
    return updated_prize
