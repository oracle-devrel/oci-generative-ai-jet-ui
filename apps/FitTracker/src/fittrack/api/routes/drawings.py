"""Drawing API routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from fittrack.api.schemas.common import DeleteResponse, PaginationMeta
from fittrack.api.schemas.drawing import DrawingCreate, DrawingUpdate
from fittrack.models.base import generate_uuid, utc_now
from fittrack.models.enums import DrawingStatus
from fittrack.repositories.drawing import DrawingRepository

router = APIRouter(prefix="/drawings", tags=["drawings"])


def get_drawing_repo() -> DrawingRepository:
    """Dependency to get drawing repository."""
    return DrawingRepository()


@router.get("")
def list_drawings(
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    status_filter: DrawingStatus | None = None,
    repo: DrawingRepository = Depends(get_drawing_repo),
) -> dict:
    """List drawings with pagination."""
    offset = (page - 1) * limit

    if status_filter:
        drawings = repo.find_by_status(status_filter, limit=limit, offset=offset)
        total = repo.count(
            "JSON_VALUE(data, '$.status') = :status",
            {"status": status_filter.value},
        )
    else:
        drawings = repo.find_all(limit=limit, offset=offset)
        total = repo.count()

    return {
        "items": drawings,
        "pagination": PaginationMeta.from_pagination(page, limit, total).model_dump(),
    }


@router.get("/open")
def list_open_drawings(
    repo: DrawingRepository = Depends(get_drawing_repo),
) -> list[dict]:
    """List all open drawings available for ticket purchase."""
    return repo.find_open_drawings()


@router.get("/{drawing_id}")
def get_drawing(
    drawing_id: str,
    repo: DrawingRepository = Depends(get_drawing_repo),
) -> dict:
    """Get a drawing by ID."""
    drawing = repo.find_by_id(drawing_id)
    if not drawing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Drawing {drawing_id} not found",
        )
    return drawing


@router.post("", status_code=status.HTTP_201_CREATED)
def create_drawing(
    drawing_data: DrawingCreate,
    repo: DrawingRepository = Depends(get_drawing_repo),
) -> dict:
    """Create a new drawing."""
    # Validate times
    if drawing_data.ticket_sales_close >= drawing_data.drawing_time:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ticket sales must close before drawing time",
        )

    # Create drawing document
    now = utc_now()
    drawing_doc = {
        "_id": generate_uuid(),
        "drawing_type": drawing_data.drawing_type.value,
        "name": drawing_data.name,
        "description": drawing_data.description,
        "ticket_cost_points": drawing_data.ticket_cost_points,
        "drawing_time": drawing_data.drawing_time.isoformat() + "Z",
        "ticket_sales_close": drawing_data.ticket_sales_close.isoformat() + "Z",
        "eligibility": drawing_data.eligibility,
        "status": drawing_data.status.value,
        "total_tickets": 0,
        "random_seed": None,
        "created_by": None,  # Set from auth in CP2
        "completed_at": None,
        "created_at": now.isoformat() + "Z",
        "updated_at": now.isoformat() + "Z",
    }

    created = repo.create(drawing_doc)
    return created


@router.put("/{drawing_id}")
def update_drawing(
    drawing_id: str,
    drawing_data: DrawingUpdate,
    repo: DrawingRepository = Depends(get_drawing_repo),
) -> dict:
    """Update a drawing."""
    drawing = repo.find_by_id(drawing_id)
    if not drawing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Drawing {drawing_id} not found",
        )

    # Check if drawing can be edited
    current_status = drawing.get("status")
    if current_status in ("completed", "cancelled"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot update drawing in {current_status} status",
        )

    # Build update document
    update_data = drawing_data.model_dump(exclude_unset=True)
    if not update_data:
        return drawing

    # Convert enums to values
    if "status" in update_data and update_data["status"]:
        update_data["status"] = update_data["status"].value
    if "drawing_type" in update_data and update_data["drawing_type"]:
        update_data["drawing_type"] = update_data["drawing_type"].value

    # Convert datetimes
    if "drawing_time" in update_data and update_data["drawing_time"]:
        update_data["drawing_time"] = update_data["drawing_time"].isoformat() + "Z"
    if "ticket_sales_close" in update_data and update_data["ticket_sales_close"]:
        update_data["ticket_sales_close"] = update_data["ticket_sales_close"].isoformat() + "Z"

    # Merge updates into existing drawing
    updated_drawing = {**drawing, **update_data}
    updated_drawing["updated_at"] = utc_now().isoformat() + "Z"

    repo.update(drawing_id, updated_drawing)
    return updated_drawing


@router.delete("/{drawing_id}")
def delete_drawing(
    drawing_id: str,
    repo: DrawingRepository = Depends(get_drawing_repo),
) -> DeleteResponse:
    """Delete a drawing."""
    drawing = repo.find_by_id(drawing_id)
    if not drawing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Drawing {drawing_id} not found",
        )

    # Only allow deletion of draft drawings
    if drawing.get("status") != "draft":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only draft drawings can be deleted",
        )

    repo.delete(drawing_id)
    return DeleteResponse(deleted=True, id=drawing_id)
