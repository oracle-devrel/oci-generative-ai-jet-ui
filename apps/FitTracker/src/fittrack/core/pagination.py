"""Pagination utilities for API responses."""

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginationParams(BaseModel):
    """Pagination request parameters."""

    page: int = Field(default=1, ge=1, description="Page number (1-indexed)")
    limit: int = Field(default=20, ge=1, le=100, description="Items per page")

    @property
    def offset(self) -> int:
        """Calculate offset for database query."""
        return (self.page - 1) * self.limit


class PaginationMeta(BaseModel):
    """Pagination metadata in response."""

    page: int = Field(description="Current page number")
    limit: int = Field(description="Items per page")
    total_items: int = Field(description="Total number of items")
    total_pages: int = Field(description="Total number of pages")
    has_next: bool = Field(description="Whether there is a next page")
    has_prev: bool = Field(description="Whether there is a previous page")


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response wrapper."""

    items: list[T]
    pagination: PaginationMeta

    @classmethod
    def create(
        cls,
        items: list[T],
        total: int,
        params: PaginationParams,
    ) -> "PaginatedResponse[T]":
        """Create a paginated response from items and count."""
        total_pages = (total + params.limit - 1) // params.limit if total > 0 else 1
        return cls(
            items=items,
            pagination=PaginationMeta(
                page=params.page,
                limit=params.limit,
                total_items=total,
                total_pages=total_pages,
                has_next=params.page < total_pages,
                has_prev=params.page > 1,
            ),
        )


def paginate_query(
    query_results: list[Any],
    total_count: int,
    params: PaginationParams,
) -> dict[str, Any]:
    """Create pagination dict for response."""
    total_pages = (total_count + params.limit - 1) // params.limit if total_count > 0 else 1
    return {
        "items": query_results,
        "pagination": {
            "page": params.page,
            "limit": params.limit,
            "total_items": total_count,
            "total_pages": total_pages,
            "has_next": params.page < total_pages,
            "has_prev": params.page > 1,
        },
    }
