"""
FastAPI web dashboard for browsing and replaying reasoning session traces.

Provides a rich web UI for:
  - Viewing recent sessions with aggregate stats
  - Filtering and searching sessions by strategy, model, status
  - Detailed event timeline with color-coded event types
  - Step-by-step replay of reasoning sessions
  - Side-by-side session comparison
  - Aggregate metrics and strategy performance breakdowns

Can be mounted at /datalake in an existing FastAPI app or run standalone.

Usage (standalone):
    uvicorn datalake.dashboard:app --host 0.0.0.0 --port 8090

Usage (mounted):
    from datalake.dashboard import create_app
    main_app.mount("/datalake", create_app())
"""

import json
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from datalake.config import get_db_config
from datalake.store import ReasoningStore

# Template directory
TEMPLATE_DIR = Path(__file__).parent / "templates"


# Jinja2 filters
def _json_pretty(value):
    """Pretty-print JSON in templates."""
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return value
    return json.dumps(value, indent=2, default=str)


def _truncate(value, length=100):
    """Truncate text with ellipsis."""
    if value and len(str(value)) > length:
        return str(value)[:length] + "..."
    return value


def _format_duration(ms):
    """Format milliseconds to human-readable duration."""
    if ms is None:
        return "N/A"
    if ms < 1000:
        return f"{ms:.0f}ms"
    if ms < 60000:
        return f"{ms / 1000:.1f}s"
    return f"{ms / 60000:.1f}m"


# Event type colors for the timeline
EVENT_COLORS = {
    "node": "#3b82f6",  # blue
    "task": "#8b5cf6",  # violet
    "sample": "#06b6d4",  # cyan
    "iteration": "#f59e0b",  # amber
    "refinement": "#10b981",  # emerald
    "pipeline": "#ec4899",  # pink
    "react_step": "#ef4444",  # red
    "chain_step": "#6366f1",  # indigo
    "text": "#94a3b8",  # slate
    "final": "#22c55e",  # green
}


def create_app(store: Optional[ReasoningStore] = None) -> FastAPI:
    """
    Create a FastAPI dashboard application.

    Args:
        store: Optional ReasoningStore instance. Creates one from env if None.

    Returns:
        Configured FastAPI application.
    """
    app = FastAPI(
        title="Reasoning Datalake Dashboard",
        description="Browse, replay, and compare agent reasoning traces",
        version="0.1.0",
    )

    templates = Jinja2Templates(directory=str(TEMPLATE_DIR))
    templates.env.filters["json_pretty"] = _json_pretty
    templates.env.filters["truncate_text"] = _truncate
    templates.env.filters["format_duration"] = _format_duration
    templates.env.globals["event_colors"] = EVENT_COLORS

    # Lazy store initialization
    _store = store

    def get_store() -> ReasoningStore:
        nonlocal _store
        if _store is None:
            _store = ReasoningStore(get_db_config())
        return _store

    # -------------------------------------------------------------------------
    # Dashboard Home
    # -------------------------------------------------------------------------

    @app.get("/", response_class=HTMLResponse)
    async def dashboard_home(request: Request):
        """Dashboard home with stats cards and recent sessions."""
        store = get_store()
        stats = store.get_stats()
        recent = store.list_sessions(limit=10)
        return templates.TemplateResponse(
            "dashboard.html",
            {
                "request": request,
                "stats": stats,
                "recent_sessions": recent["sessions"],
                "page_title": "Dashboard",
            },
        )

    # -------------------------------------------------------------------------
    # Sessions List
    # -------------------------------------------------------------------------

    @app.get("/sessions", response_class=HTMLResponse)
    async def sessions_list(
        request: Request,
        strategy: Optional[str] = Query(None),
        model: Optional[str] = Query(None),
        status: Optional[str] = Query(None),
        q: Optional[str] = Query(None),
        limit: int = Query(50, ge=1, le=200),
        offset: int = Query(0, ge=0),
    ):
        """Filterable session list."""
        store = get_store()

        if q:
            sessions_list = store.search_sessions(q, limit=limit)
            total = len(sessions_list)
            result = {"sessions": sessions_list, "total": total, "limit": limit, "offset": 0}
        else:
            result = store.list_sessions(
                strategy=strategy,
                model=model,
                status=status,
                limit=limit,
                offset=offset,
            )

        # Get distinct strategies and models for filter dropdowns
        stats = store.get_stats()
        strategies = sorted(stats.get("by_strategy", {}).keys())
        models = sorted(stats.get("by_model", {}).keys())

        return templates.TemplateResponse(
            "sessions.html",
            {
                "request": request,
                "sessions": result["sessions"],
                "total": result["total"],
                "limit": limit,
                "offset": offset,
                "strategies": strategies,
                "models": models,
                "filters": {
                    "strategy": strategy,
                    "model": model,
                    "status": status,
                    "q": q,
                },
                "page_title": "Sessions",
            },
        )

    # -------------------------------------------------------------------------
    # Session Detail
    # -------------------------------------------------------------------------

    @app.get("/sessions/{session_id}", response_class=HTMLResponse)
    async def session_detail(request: Request, session_id: str):
        """Session detail with event timeline."""
        store = get_store()
        session = store.get_session(session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="Session not found")

        return templates.TemplateResponse(
            "trace_detail.html",
            {
                "request": request,
                "session": session,
                "events": session.get("events", []),
                "metrics": session.get("metrics"),
                "event_colors": EVENT_COLORS,
                "page_title": f"Session {session_id[:8]}...",
            },
        )

    # -------------------------------------------------------------------------
    # Session Replay
    # -------------------------------------------------------------------------

    @app.get("/sessions/{session_id}/replay", response_class=HTMLResponse)
    async def session_replay(request: Request, session_id: str):
        """Step-by-step replay view."""
        store = get_store()
        session = store.get_session(session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="Session not found")

        events = list(store.replay_session(session_id))

        return templates.TemplateResponse(
            "trace_detail.html",
            {
                "request": request,
                "session": session,
                "events": events,
                "metrics": session.get("metrics"),
                "event_colors": EVENT_COLORS,
                "replay_mode": True,
                "page_title": f"Replay {session_id[:8]}...",
            },
        )

    # -------------------------------------------------------------------------
    # Compare Sessions
    # -------------------------------------------------------------------------

    @app.get("/compare", response_class=HTMLResponse)
    async def compare_sessions(
        request: Request,
        ids: Optional[str] = Query(None, description="Comma-separated session IDs"),
    ):
        """Side-by-side session comparison."""
        store = get_store()

        comparison = None
        sessions = []
        if ids:
            session_ids = [s.strip() for s in ids.split(",") if s.strip()]
            comparison = store.compare_sessions(session_ids)
            sessions = comparison.get("sessions", [])

        # Get recent sessions for selection
        recent = store.list_sessions(limit=20)

        return templates.TemplateResponse(
            "sessions.html",
            {
                "request": request,
                "sessions": recent["sessions"],
                "total": recent["total"],
                "limit": 20,
                "offset": 0,
                "strategies": [],
                "models": [],
                "filters": {},
                "comparison": comparison,
                "compare_sessions": sessions,
                "compare_mode": True,
                "page_title": "Compare Sessions",
            },
        )

    # -------------------------------------------------------------------------
    # Stats
    # -------------------------------------------------------------------------

    @app.get("/stats", response_class=HTMLResponse)
    async def stats_page(request: Request):
        """Aggregate metrics and statistics."""
        store = get_store()
        stats = store.get_stats()

        return templates.TemplateResponse(
            "dashboard.html",
            {
                "request": request,
                "stats": stats,
                "recent_sessions": [],
                "stats_mode": True,
                "page_title": "Statistics",
            },
        )

    # -------------------------------------------------------------------------
    # API Endpoints (JSON)
    # -------------------------------------------------------------------------

    @app.get("/api/sessions/{session_id}")
    async def api_session_detail(session_id: str):
        """JSON API: get session detail."""
        store = get_store()
        session = store.get_session(session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="Session not found")
        return JSONResponse(content=session)

    @app.get("/api/sessions/{session_id}/events")
    async def api_session_events(session_id: str):
        """JSON API: get session events."""
        store = get_store()
        events = list(store.replay_session(session_id))
        return JSONResponse(content=events)

    @app.get("/api/stats")
    async def api_stats():
        """JSON API: aggregate stats."""
        store = get_store()
        return JSONResponse(content=store.get_stats())

    return app


# Standalone app instance
app = create_app()


def main():
    """Run the dashboard as a standalone server."""
    import argparse

    import uvicorn

    parser = argparse.ArgumentParser(description="Reasoning Datalake Dashboard")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8090, help="Port to bind to")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    args = parser.parse_args()

    uvicorn.run(
        "datalake.dashboard:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()
