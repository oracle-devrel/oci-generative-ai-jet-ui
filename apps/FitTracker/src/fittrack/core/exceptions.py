"""Custom exceptions and RFC 7807 error handling."""

from typing import Any

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel


class ErrorDetail(BaseModel):
    """RFC 7807 Problem Details error response."""

    type: str
    title: str
    status: int
    detail: str
    instance: str | None = None
    errors: list[dict[str, Any]] | None = None


class FitTrackException(Exception):
    """Base exception for FitTrack application."""

    def __init__(
        self,
        message: str,
        error_type: str = "https://fittrack.com/errors/internal",
        status_code: int = 500,
        errors: list[dict[str, Any]] | None = None,
    ) -> None:
        self.message = message
        self.error_type = error_type
        self.status_code = status_code
        self.errors = errors
        super().__init__(message)


class NotFoundError(FitTrackException):
    """Resource not found error."""

    def __init__(self, resource: str, identifier: str | None = None) -> None:
        detail = f"{resource} not found"
        if identifier:
            detail = f"{resource} with id '{identifier}' not found"
        super().__init__(
            message=detail,
            error_type="https://fittrack.com/errors/not-found",
            status_code=404,
        )


class ValidationError(FitTrackException):
    """Validation error."""

    def __init__(self, message: str, errors: list[dict[str, Any]] | None = None) -> None:
        super().__init__(
            message=message,
            error_type="https://fittrack.com/errors/validation",
            status_code=400,
            errors=errors,
        )


class ConflictError(FitTrackException):
    """Resource conflict error (e.g., duplicate)."""

    def __init__(self, message: str) -> None:
        super().__init__(
            message=message,
            error_type="https://fittrack.com/errors/conflict",
            status_code=409,
        )


class UnauthorizedError(FitTrackException):
    """Authentication required error."""

    def __init__(self, message: str = "Authentication required") -> None:
        super().__init__(
            message=message,
            error_type="https://fittrack.com/errors/unauthorized",
            status_code=401,
        )


class ForbiddenError(FitTrackException):
    """Permission denied error."""

    def __init__(self, message: str = "Permission denied") -> None:
        super().__init__(
            message=message,
            error_type="https://fittrack.com/errors/forbidden",
            status_code=403,
        )


class InsufficientPointsError(FitTrackException):
    """Not enough points for operation."""

    def __init__(self, required: int, available: int) -> None:
        super().__init__(
            message=f"Insufficient points. Required: {required}, Available: {available}",
            error_type="https://fittrack.com/errors/insufficient-points",
            status_code=400,
        )


class DrawingClosedError(FitTrackException):
    """Drawing is not open for ticket purchases."""

    def __init__(self, drawing_id: str) -> None:
        super().__init__(
            message=f"Drawing '{drawing_id}' is not open for ticket purchases",
            error_type="https://fittrack.com/errors/drawing-closed",
            status_code=400,
        )


class IneligibleUserError(FitTrackException):
    """User is not eligible for operation."""

    def __init__(self, reason: str) -> None:
        super().__init__(
            message=f"User is not eligible: {reason}",
            error_type="https://fittrack.com/errors/ineligible",
            status_code=403,
        )


class DatabaseError(FitTrackException):
    """Database operation error."""

    def __init__(self, message: str = "Database operation failed") -> None:
        super().__init__(
            message=message,
            error_type="https://fittrack.com/errors/database",
            status_code=500,
        )


class OptimisticLockError(FitTrackException):
    """Optimistic lock conflict (concurrent modification)."""

    def __init__(self, resource: str) -> None:
        super().__init__(
            message=f"Concurrent modification detected for {resource}. Please retry.",
            error_type="https://fittrack.com/errors/optimistic-lock",
            status_code=409,
        )


async def fittrack_exception_handler(request: Request, exc: FitTrackException) -> JSONResponse:
    """Handle FitTrack exceptions with RFC 7807 format."""
    error = ErrorDetail(
        type=exc.error_type,
        title=exc.error_type.split("/")[-1].replace("-", " ").title(),
        status=exc.status_code,
        detail=exc.message,
        instance=str(request.url.path),
        errors=exc.errors,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=error.model_dump(exclude_none=True),
        headers={"Content-Type": "application/problem+json"},
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle FastAPI HTTPExceptions with RFC 7807 format."""
    error = ErrorDetail(
        type=f"https://fittrack.com/errors/http-{exc.status_code}",
        title=f"HTTP {exc.status_code}",
        status=exc.status_code,
        detail=str(exc.detail),
        instance=str(request.url.path),
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=error.model_dump(exclude_none=True),
        headers={"Content-Type": "application/problem+json"},
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions with RFC 7807 format."""
    error = ErrorDetail(
        type="https://fittrack.com/errors/internal",
        title="Internal Server Error",
        status=500,
        detail="An unexpected error occurred",
        instance=str(request.url.path),
    )
    return JSONResponse(
        status_code=500,
        content=error.model_dump(exclude_none=True),
        headers={"Content-Type": "application/problem+json"},
    )
