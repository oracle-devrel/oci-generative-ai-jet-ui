"""Sponsor API routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from fittrack.api.schemas.common import DeleteResponse, PaginationMeta
from fittrack.api.schemas.sponsor import SponsorCreate, SponsorUpdate
from fittrack.models.base import generate_uuid, utc_now
from fittrack.repositories.sponsor import SponsorRepository

router = APIRouter(prefix="/sponsors", tags=["sponsors"])


def get_sponsor_repo() -> SponsorRepository:
    """Dependency to get sponsor repository."""
    return SponsorRepository()


@router.get("")
def list_sponsors(
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    active_only: bool = False,
    repo: SponsorRepository = Depends(get_sponsor_repo),
) -> dict:
    """List sponsors with pagination."""
    offset = (page - 1) * limit

    if active_only:
        sponsors = repo.find_active(limit=limit, offset=offset)
        total = repo.count(
            "JSON_VALUE(data, '$.status') = 'active'",
        )
    else:
        sponsors = repo.find_all(limit=limit, offset=offset)
        total = repo.count()

    return {
        "items": sponsors,
        "pagination": PaginationMeta.from_pagination(page, limit, total).model_dump(),
    }


@router.get("/search")
def search_sponsors(
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = 10,
    repo: SponsorRepository = Depends(get_sponsor_repo),
) -> list[dict]:
    """Search sponsors by name."""
    return repo.search_by_name(q, limit=limit)


@router.get("/{sponsor_id}")
def get_sponsor(
    sponsor_id: str,
    repo: SponsorRepository = Depends(get_sponsor_repo),
) -> dict:
    """Get a sponsor by ID."""
    sponsor = repo.find_by_id(sponsor_id)
    if not sponsor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sponsor {sponsor_id} not found",
        )
    return sponsor


@router.post("", status_code=status.HTTP_201_CREATED)
def create_sponsor(
    sponsor_data: SponsorCreate,
    repo: SponsorRepository = Depends(get_sponsor_repo),
) -> dict:
    """Create a new sponsor."""
    # Check for duplicate name
    existing = repo.find_by_name(sponsor_data.name)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Sponsor with name '{sponsor_data.name}' already exists",
        )

    # Create sponsor document
    now = utc_now()
    sponsor_doc = {
        "_id": generate_uuid(),
        "name": sponsor_data.name,
        "contact_name": sponsor_data.contact_name,
        "contact_email": sponsor_data.contact_email,
        "contact_phone": sponsor_data.contact_phone,
        "website_url": sponsor_data.website_url,
        "logo_url": sponsor_data.logo_url,
        "status": sponsor_data.status.value,
        "notes": sponsor_data.notes,
        "created_at": now.isoformat() + "Z",
        "updated_at": now.isoformat() + "Z",
    }

    created = repo.create(sponsor_doc)
    return created


@router.put("/{sponsor_id}")
def update_sponsor(
    sponsor_id: str,
    sponsor_data: SponsorUpdate,
    repo: SponsorRepository = Depends(get_sponsor_repo),
) -> dict:
    """Update a sponsor."""
    sponsor = repo.find_by_id(sponsor_id)
    if not sponsor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sponsor {sponsor_id} not found",
        )

    # Build update document
    update_data = sponsor_data.model_dump(exclude_unset=True)
    if not update_data:
        return sponsor

    # Convert enums to values
    if "status" in update_data and update_data["status"]:
        update_data["status"] = update_data["status"].value

    # Check name uniqueness if changing
    if "name" in update_data and update_data["name"] != sponsor.get("name"):
        existing = repo.find_by_name(update_data["name"])
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Sponsor with name '{update_data['name']}' already exists",
            )

    # Merge updates into existing sponsor
    updated_sponsor = {**sponsor, **update_data}
    updated_sponsor["updated_at"] = utc_now().isoformat() + "Z"

    repo.update(sponsor_id, updated_sponsor)
    return updated_sponsor


@router.delete("/{sponsor_id}")
def delete_sponsor(
    sponsor_id: str,
    repo: SponsorRepository = Depends(get_sponsor_repo),
) -> DeleteResponse:
    """Delete a sponsor."""
    sponsor = repo.find_by_id(sponsor_id)
    if not sponsor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sponsor {sponsor_id} not found",
        )

    repo.delete(sponsor_id)
    return DeleteResponse(deleted=True, id=sponsor_id)
