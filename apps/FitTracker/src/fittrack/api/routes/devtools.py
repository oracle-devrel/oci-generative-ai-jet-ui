"""Development tools routes - disabled in production."""

import subprocess
import sys
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse, Response

from fittrack.core.config import get_settings

router = APIRouter()

# Path to devtools directory
DEVTOOLS_DIR = Path(__file__).parent.parent.parent.parent.parent / "devtools"
SCRIPTS_DIR = Path(__file__).parent.parent.parent.parent.parent / "scripts"


def check_dev_mode():
    """Check if in development mode, raise 404 if not."""
    settings = get_settings()
    if not settings.is_development:
        raise HTTPException(status_code=404, detail="Not found")


@router.get("/", response_class=HTMLResponse)
async def devtools_page() -> HTMLResponse:
    """Serve the development test page."""
    check_dev_mode()

    test_page = DEVTOOLS_DIR / "test_page.html"
    if not test_page.exists():
        return HTMLResponse(
            content="""
            <!DOCTYPE html>
            <html>
            <head><title>FitTrack DevTools</title></head>
            <body>
                <h1>FitTrack DevTools</h1>
                <p>Test page not yet created. Run the full setup to generate it.</p>
                <p>API Docs: <a href="/docs">/docs</a></p>
            </body>
            </html>
            """,
            status_code=200,
        )

    return HTMLResponse(content=test_page.read_text(), status_code=200)


@router.get("/styles.css")
async def devtools_css() -> Response:
    """Serve the devtools CSS file."""
    check_dev_mode()

    css_file = DEVTOOLS_DIR / "styles.css"
    if not css_file.exists():
        raise HTTPException(status_code=404, detail="CSS file not found")

    return Response(
        content=css_file.read_text(),
        media_type="text/css",
    )


@router.get("/app.js")
async def devtools_js() -> Response:
    """Serve the devtools JavaScript file."""
    check_dev_mode()

    js_file = DEVTOOLS_DIR / "app.js"
    if not js_file.exists():
        raise HTTPException(status_code=404, detail="JavaScript file not found")

    return Response(
        content=js_file.read_text(),
        media_type="application/javascript",
    )


@router.post("/seed")
async def seed_database() -> dict[str, str]:
    """Seed the database with synthetic data."""
    check_dev_mode()

    seed_script = SCRIPTS_DIR / "seed_data.py"
    if not seed_script.exists():
        raise HTTPException(
            status_code=500,
            detail="Seed script not found",
        )

    try:
        # Run the seed script
        result = subprocess.run(
            [sys.executable, str(seed_script)],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )

        if result.returncode != 0:
            return {
                "status": "error",
                "message": f"Seeding failed: {result.stderr}",
            }

        return {
            "status": "success",
            "message": "Database seeded successfully",
            "output": result.stdout[-1000:] if len(result.stdout) > 1000 else result.stdout,
        }
    except subprocess.TimeoutExpired:
        return {
            "status": "error",
            "message": "Seeding timed out after 120 seconds",
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Seeding error: {e!s}",
        }


@router.post("/reset")
async def reset_database() -> dict[str, str]:
    """Reset the database (drop all data, run migrations, then seed)."""
    check_dev_mode()

    # For safety, just return a message indicating this needs manual implementation
    return {
        "status": "warning",
        "message": "Database reset requires running: make db-reset",
        "instructions": [
            "1. Stop the application",
            "2. Run: make db-reset",
            "3. Restart the application",
        ],
    }
