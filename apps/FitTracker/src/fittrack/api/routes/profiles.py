"""Profile API routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from fittrack.api.schemas.common import PaginationMeta
from fittrack.api.schemas.profile import ProfileCreate, ProfileUpdate
from fittrack.models.base import generate_uuid, utc_now
from fittrack.models.profile import calculate_age_bracket, calculate_tier_code
from fittrack.repositories.profile import ProfileRepository

router = APIRouter(prefix="/profiles", tags=["profiles"])


def get_profile_repo() -> ProfileRepository:
    """Dependency to get profile repository."""
    return ProfileRepository()


@router.get("")
def list_profiles(
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    tier: str | None = None,
    repo: ProfileRepository = Depends(get_profile_repo),
) -> dict:
    """List all profiles with pagination."""
    offset = (page - 1) * limit

    if tier:
        profiles = repo.find_by_tier(tier, limit=limit, offset=offset)
        total = repo.count_by_tier(tier)
    else:
        profiles = repo.find_all(limit=limit, offset=offset)
        total = repo.count()

    return {
        "items": profiles,
        "pagination": PaginationMeta.from_pagination(page, limit, total).model_dump(),
    }


@router.get("/{profile_id}")
def get_profile(
    profile_id: str,
    repo: ProfileRepository = Depends(get_profile_repo),
) -> dict:
    """Get a profile by ID."""
    profile = repo.find_by_id(profile_id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Profile {profile_id} not found",
        )
    return profile


@router.get("/user/{user_id}")
def get_profile_by_user(
    user_id: str,
    repo: ProfileRepository = Depends(get_profile_repo),
) -> dict:
    """Get a profile by user ID."""
    profile = repo.find_by_user_id(user_id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Profile for user {user_id} not found",
        )
    return profile


@router.post("", status_code=status.HTTP_201_CREATED)
def create_profile(
    profile_data: ProfileCreate,
    repo: ProfileRepository = Depends(get_profile_repo),
) -> dict:
    """Create a new profile."""
    # Check for existing profile
    existing = repo.find_by_user_id(profile_data.user_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Profile for user {profile_data.user_id} already exists",
        )

    # Calculate derived fields
    age_bracket = calculate_age_bracket(profile_data.date_of_birth)
    tier_code = calculate_tier_code(
        profile_data.biological_sex.value,
        age_bracket,
        profile_data.fitness_level.value,
    )

    # Create profile document
    now = utc_now()
    profile_doc = {
        "_id": generate_uuid(),
        "user_id": profile_data.user_id,
        "display_name": profile_data.display_name,
        "date_of_birth": profile_data.date_of_birth.isoformat(),
        "state_of_residence": profile_data.state_of_residence.upper(),
        "biological_sex": profile_data.biological_sex.value,
        "fitness_level": profile_data.fitness_level.value,
        "age_bracket": age_bracket,
        "tier_code": tier_code,
        "height_inches": profile_data.height_inches,
        "weight_pounds": profile_data.weight_pounds,
        "goals": profile_data.goals,
        "created_at": now.isoformat() + "Z",
        "updated_at": now.isoformat() + "Z",
    }

    created = repo.create(profile_doc)
    return created


@router.put("/{profile_id}")
def update_profile(
    profile_id: str,
    profile_data: ProfileUpdate,
    repo: ProfileRepository = Depends(get_profile_repo),
) -> dict:
    """Update a profile."""
    profile = repo.find_by_id(profile_id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Profile {profile_id} not found",
        )

    # Build update document
    update_data = profile_data.model_dump(exclude_unset=True)
    if not update_data:
        return profile

    # Convert enums to values
    if "fitness_level" in update_data and update_data["fitness_level"]:
        update_data["fitness_level"] = update_data["fitness_level"].value
        # Recalculate tier code
        tier_code = calculate_tier_code(
            profile.get("biological_sex"),
            profile.get("age_bracket"),
            update_data["fitness_level"],
        )
        update_data["tier_code"] = tier_code

    if "state_of_residence" in update_data:
        update_data["state_of_residence"] = update_data["state_of_residence"].upper()

    # Merge updates into existing profile
    updated_profile = {**profile, **update_data}
    updated_profile["updated_at"] = utc_now().isoformat() + "Z"

    repo.update(profile_id, updated_profile)
    return updated_profile
