"""Common API schemas for pagination and errors."""

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class PaginationRequest(BaseModel):
    """Pagination request parameters."""

    page: int = Field(default=1, ge=1, description="Page number (1-indexed)")
    limit: int = Field(default=20, ge=1, le=100, description="Items per page")

    @property
    def offset(self) -> int:
        """Calculate offset from page and limit."""
        return (self.page - 1) * self.limit


class PaginationMeta(BaseModel):
    """Pagination metadata in response."""

    page: int = Field(description="Current page number")
    limit: int = Field(description="Items per page")
    total: int = Field(description="Total number of items")
    total_pages: int = Field(description="Total number of pages")
    has_next: bool = Field(description="Whether there is a next page")
    has_prev: bool = Field(description="Whether there is a previous page")

    @classmethod
    def from_pagination(
        cls,
        page: int,
        limit: int,
        total: int,
    ) -> "PaginationMeta":
        """Create pagination meta from values."""
        total_pages = (total + limit - 1) // limit if limit > 0 else 0
        return cls(
            page=page,
            limit=limit,
            total=total,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1,
        )


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response."""

    items: list[T]
    pagination: PaginationMeta


class ErrorResponse(BaseModel):
    """RFC 7807 Problem Details error response."""

    model_config = ConfigDict(populate_by_name=True)

    type: str = Field(
        description="URI reference identifying the problem type",
        examples=["https://fittrack.com/errors/insufficient-points"],
    )
    title: str = Field(
        description="Short, human-readable summary of the problem",
        examples=["Insufficient Points"],
    )
    status: int = Field(
        description="HTTP status code",
        examples=[400, 404, 500],
    )
    detail: str = Field(
        description="Human-readable explanation specific to this occurrence",
        examples=["You need 500 points but only have 350"],
    )
    instance: str | None = Field(
        default=None,
        description="URI reference identifying the specific occurrence",
        examples=["/api/v1/drawings/abc123/tickets"],
    )
    errors: list[dict[str, Any]] | None = Field(
        default=None,
        description="Additional validation errors",
    )


class SuccessResponse(BaseModel):
    """Generic success response."""

    success: bool = True
    message: str | None = None


class DeleteResponse(BaseModel):
    """Response for delete operations."""

    deleted: bool = True
    id: str
