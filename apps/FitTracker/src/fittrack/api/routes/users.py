"""User API routes."""

import hashlib
import secrets
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from fittrack.api.schemas.common import DeleteResponse, PaginationMeta
from fittrack.api.schemas.user import (
    UserCreate,
    UserUpdate,
)
from fittrack.models.base import generate_uuid, utc_now
from fittrack.models.enums import UserRole, UserStatus
from fittrack.repositories.user import UserRepository

router = APIRouter(prefix="/users", tags=["users"])


def get_user_repo() -> UserRepository:
    """Dependency to get user repository."""
    return UserRepository()


def hash_password(password: str) -> str:
    """Hash password using SHA-256 (placeholder for Argon2id in CP2)."""
    salt = secrets.token_hex(16)
    hash_value = hashlib.sha256(f"{salt}{password}".encode()).hexdigest()
    return f"{salt}${hash_value}"


@router.get("")
def list_users(
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    repo: UserRepository = Depends(get_user_repo),
) -> dict:
    """List all users with pagination."""
    offset = (page - 1) * limit
    users = repo.find_all(limit=limit, offset=offset)
    total = repo.count()

    return {
        "items": users,
        "pagination": PaginationMeta.from_pagination(page, limit, total).model_dump(),
    }


@router.get("/{user_id}")
def get_user(
    user_id: str,
    repo: UserRepository = Depends(get_user_repo),
) -> dict:
    """Get a user by ID."""
    user = repo.find_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found",
        )
    return user


@router.post("", status_code=status.HTTP_201_CREATED)
def create_user(
    user_data: UserCreate,
    repo: UserRepository = Depends(get_user_repo),
) -> dict:
    """Create a new user."""
    # Check for duplicate email
    existing = repo.find_by_email(user_data.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"User with email {user_data.email} already exists",
        )

    # Create user document
    now = utc_now()
    user_doc = {
        "_id": generate_uuid(),
        "email": user_data.email,
        "password_hash": hash_password(user_data.password),
        "email_verified": False,
        "email_verified_at": None,
        "status": UserStatus.PENDING.value,
        "role": UserRole.USER.value,
        "premium_expires_at": None,
        "point_balance": 0,
        "last_login_at": None,
        "created_at": now.isoformat() + "Z",
        "updated_at": now.isoformat() + "Z",
        "version": 1,
    }

    created = repo.create(user_doc)
    return created


@router.put("/{user_id}")
def update_user(
    user_id: str,
    user_data: UserUpdate,
    repo: UserRepository = Depends(get_user_repo),
) -> dict:
    """Update a user."""
    user = repo.find_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found",
        )

    # Build update document
    update_data = user_data.model_dump(exclude_unset=True)
    if not update_data:
        return user

    # Convert enums to values
    if "status" in update_data and update_data["status"]:
        update_data["status"] = update_data["status"].value
    if "role" in update_data and update_data["role"]:
        update_data["role"] = update_data["role"].value

    # Check email uniqueness if changing
    if "email" in update_data and update_data["email"] != user.get("email"):
        existing = repo.find_by_email(update_data["email"])
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"User with email {update_data['email']} already exists",
            )

    # Merge updates into existing user
    updated_user = {**user, **update_data}
    updated_user["updated_at"] = utc_now().isoformat() + "Z"

    repo.update(user_id, updated_user)
    return updated_user


@router.delete("/{user_id}")
def delete_user(
    user_id: str,
    repo: UserRepository = Depends(get_user_repo),
) -> DeleteResponse:
    """Delete a user."""
    user = repo.find_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found",
        )

    repo.delete(user_id)
    return DeleteResponse(deleted=True, id=user_id)
