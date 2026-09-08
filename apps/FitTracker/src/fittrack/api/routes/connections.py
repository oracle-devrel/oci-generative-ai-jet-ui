"""Tracker connection API routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from fittrack.api.schemas.common import DeleteResponse, PaginationMeta
from fittrack.api.schemas.connection import ConnectionCreate
from fittrack.models.base import generate_uuid, utc_now
from fittrack.models.enums import SyncStatus
from fittrack.repositories.connection import ConnectionRepository

router = APIRouter(prefix="/connections", tags=["connections"])


def get_connection_repo() -> ConnectionRepository:
    """Dependency to get connection repository."""
    return ConnectionRepository()


@router.get("")
def list_connections(
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    user_id: str | None = None,
    repo: ConnectionRepository = Depends(get_connection_repo),
) -> dict:
    """List all connections with pagination."""
    offset = (page - 1) * limit

    if user_id:
        connections = repo.find_by_user(user_id)
        # Apply pagination to filtered results
        total = len(connections)
        connections = connections[offset : offset + limit]
    else:
        connections = repo.find_all(limit=limit, offset=offset)
        total = repo.count()

    return {
        "items": connections,
        "pagination": PaginationMeta.from_pagination(page, limit, total).model_dump(),
    }


@router.get("/{connection_id}")
def get_connection(
    connection_id: str,
    repo: ConnectionRepository = Depends(get_connection_repo),
) -> dict:
    """Get a connection by ID."""
    connection = repo.find_by_id(connection_id)
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Connection {connection_id} not found",
        )
    return connection


@router.post("", status_code=status.HTTP_201_CREATED)
def create_connection(
    connection_data: ConnectionCreate,
    repo: ConnectionRepository = Depends(get_connection_repo),
) -> dict:
    """Create a new tracker connection."""
    # Check for existing connection
    existing = repo.find_by_user_and_provider(connection_data.user_id, connection_data.provider)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Connection for user {connection_data.user_id} with provider {connection_data.provider.value} already exists",
        )

    # Create connection document
    now = utc_now()
    connection_doc = {
        "_id": generate_uuid(),
        "user_id": connection_data.user_id,
        "provider": connection_data.provider.value,
        "is_primary": connection_data.is_primary,
        "access_token": None,
        "refresh_token": None,
        "token_expires_at": None,
        "last_sync_at": None,
        "sync_status": SyncStatus.PENDING.value,
        "error_message": None,
        "created_at": now.isoformat() + "Z",
        "updated_at": now.isoformat() + "Z",
    }

    created = repo.create(connection_doc)
    return created


@router.delete("/{connection_id}")
def delete_connection(
    connection_id: str,
    repo: ConnectionRepository = Depends(get_connection_repo),
) -> DeleteResponse:
    """Delete a connection."""
    connection = repo.find_by_id(connection_id)
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Connection {connection_id} not found",
        )

    repo.delete(connection_id)
    return DeleteResponse(deleted=True, id=connection_id)
