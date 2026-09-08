"""Activity API routes."""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from fittrack.api.schemas.activity import ActivityCreate
from fittrack.api.schemas.common import PaginationMeta
from fittrack.models.base import generate_uuid, utc_now
from fittrack.repositories.activity import ActivityRepository

router = APIRouter(prefix="/activities", tags=["activities"])


def get_activity_repo() -> ActivityRepository:
    """Dependency to get activity repository."""
    return ActivityRepository()


@router.get("")
def list_activities(
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    user_id: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    repo: ActivityRepository = Depends(get_activity_repo),
) -> dict:
    """List activities with pagination and optional filters."""
    offset = (page - 1) * limit

    if user_id and start_date and end_date:
        activities = repo.find_by_user_and_date_range(user_id, start_date, end_date)
        total = len(activities)
        activities = activities[offset : offset + limit]
    elif user_id:
        activities = repo.find_by_user(user_id, limit=limit, offset=offset)
        total = repo.count(
            "JSON_VALUE(data, '$.user_id') = :user_id",
            {"user_id": user_id},
        )
    else:
        activities = repo.find_all(limit=limit, offset=offset)
        total = repo.count()

    return {
        "items": activities,
        "pagination": PaginationMeta.from_pagination(page, limit, total).model_dump(),
    }


@router.get("/{activity_id}")
def get_activity(
    activity_id: str,
    repo: ActivityRepository = Depends(get_activity_repo),
) -> dict:
    """Get an activity by ID."""
    activity = repo.find_by_id(activity_id)
    if not activity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Activity {activity_id} not found",
        )
    return activity


@router.post("", status_code=status.HTTP_201_CREATED)
def create_activity(
    activity_data: ActivityCreate,
    repo: ActivityRepository = Depends(get_activity_repo),
) -> dict:
    """Create a new activity."""
    # Check for duplicate external_id
    if activity_data.external_id:
        existing = repo.find_by_external_id(activity_data.external_id)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Activity with external_id {activity_data.external_id} already exists",
            )

    # Create activity document
    now = utc_now()
    activity_doc = {
        "_id": generate_uuid(),
        "user_id": activity_data.user_id,
        "connection_id": activity_data.connection_id,
        "external_id": activity_data.external_id,
        "activity_type": activity_data.activity_type.value,
        "start_time": activity_data.start_time.isoformat() + "Z",
        "end_time": activity_data.end_time.isoformat() + "Z" if activity_data.end_time else None,
        "duration_minutes": activity_data.duration_minutes,
        "intensity": activity_data.intensity.value if activity_data.intensity else None,
        "metrics": activity_data.metrics,
        "points_earned": 0,
        "processed": False,
        "created_at": now.isoformat() + "Z",
        "updated_at": now.isoformat() + "Z",
    }

    created = repo.create(activity_doc)
    return created
