"""FitTrack FastAPI application."""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from fittrack.core.config import get_settings
from fittrack.core.database import close_pool, init_pool
from fittrack.core.exceptions import (
    FitTrackException,
    fittrack_exception_handler,
    generic_exception_handler,
    http_exception_handler,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler."""
    settings = get_settings()
    logger.info(f"Starting {settings.app_name} in {settings.app_env} mode")

    # Startup
    try:
        init_pool()
        logger.info("Database pool initialized")
    except Exception as e:
        logger.warning(f"Failed to initialize database pool: {e}")

    yield

    # Shutdown
    close_pool()
    logger.info("Application shutdown complete")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        description="Gamified fitness platform with sweepstakes rewards",
        version="0.1.0",
        docs_url="/docs" if settings.is_development else None,
        redoc_url="/redoc" if settings.is_development else None,
        openapi_url="/openapi.json" if settings.is_development else None,
        lifespan=lifespan,
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register exception handlers
    app.add_exception_handler(FitTrackException, fittrack_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)

    # Register routers
    from fittrack.api.routes import health

    app.include_router(health.router, tags=["Health"])

    # Register API v1 routers
    from fittrack.api.routes import (
        activities,
        connections,
        drawings,
        fulfillments,
        prizes,
        profiles,
        sponsors,
        tickets,
        transactions,
        users,
    )

    api_prefix = settings.api_v1_prefix

    app.include_router(users.router, prefix=api_prefix)
    app.include_router(profiles.router, prefix=api_prefix)
    app.include_router(connections.router, prefix=api_prefix)
    app.include_router(activities.router, prefix=api_prefix)
    app.include_router(transactions.router, prefix=api_prefix)
    app.include_router(drawings.router, prefix=api_prefix)
    app.include_router(tickets.router, prefix=api_prefix)
    app.include_router(prizes.router, prefix=api_prefix)
    app.include_router(fulfillments.router, prefix=api_prefix)
    app.include_router(sponsors.router, prefix=api_prefix)

    # Register devtools routes (development only)
    if settings.is_development:
        from fittrack.api.routes import devtools

        app.include_router(devtools.router, prefix="/devtools", tags=["DevTools"])

    return app


# Create the application instance
app = create_app()
