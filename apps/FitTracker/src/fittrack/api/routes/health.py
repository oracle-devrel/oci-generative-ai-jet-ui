"""Health check endpoints."""

from fastapi import APIRouter

from fittrack.core.database import health_check as db_health_check

router = APIRouter()


@router.get("/health/live")
async def liveness() -> dict[str, str]:
    """Liveness probe - always returns OK if the service is running."""
    return {"status": "ok"}


@router.get("/health/ready")
async def readiness() -> dict[str, str | bool]:
    """Readiness probe - checks if all dependencies are ready."""
    db_ok = db_health_check()

    if not db_ok:
        return {
            "status": "not ready",
            "database": False,
        }

    return {
        "status": "ready",
        "database": True,
    }


@router.get("/health")
async def health() -> dict[str, str]:
    """Simple health check endpoint."""
    return {"status": "healthy", "service": "fittrack"}
