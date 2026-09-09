"""FastAPI service for the soccer analytics agent."""

from __future__ import annotations

import os
import uuid
import logging
from dataclasses import asdict
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from soccer_agent.agent.feature_runtime import get_runtime
from soccer_agent.agent.loop import run_turn
from soccer_agent.db import get_connection
from soccer_agent.inference.live import predict as live_predict
from soccer_agent.memory.episodic import EpisodicMemory
from soccer_agent.observability.langgraph_steps import list_steps

# Prefer the built Vite front-end (frontend/dist). Fall back to the bundled
# static/ page so the app still boots before a front-end build exists — but
# log loudly, because the fallback means the premium UI is NOT being served
# (run `npm run build` in frontend/ to fix). A silent fallback would let the
# old single-file UI reappear unnoticed.
LOGGER = logging.getLogger(__name__)
_DIST_DIR = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
_FALLBACK_DIR = Path(__file__).parent / "static"
if _DIST_DIR.exists():
    STATIC_DIR = _DIST_DIR
    LOGGER.info("Serving built front-end from %s", _DIST_DIR)
else:
    STATIC_DIR = _FALLBACK_DIR
    LOGGER.warning(
        "frontend/dist not found — serving the fallback static UI from %s. "
        "Run `npm ci && npm run build` in frontend/ to serve the React app.",
        _FALLBACK_DIR,
    )

app = FastAPI(title="Soccer Analytics Agent")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"],
    allow_methods=["*"], allow_headers=["*"],
)


class ChatRequest(BaseModel):
    session_id: str | None = None
    message: str


class PredictRequest(BaseModel):
    home_team: str
    away_team: str
    neutral: bool = True


@app.get("/health")
def health() -> dict[str, Any]:
    oracle_ok = True
    try:
        with get_connection() as conn:
            conn.cursor().execute("SELECT 1 FROM DUAL").fetchone()
    except Exception:
        oracle_ok = False
    grok_configured = all(
        os.environ.get(k)
        for k in ("OCI_GENAI_MODEL_ID", "OCI_GENAI_API_KEY", "OCI_GENAI_ENDPOINT")
    )
    return {"oracle": oracle_ok, "grok_configured": grok_configured}


@app.post("/chat")
def chat(req: ChatRequest) -> Any:
    session_id = req.session_id or f"s-{uuid.uuid4()}"
    try:
        reply = run_turn(session_id, req.message)
        return {"session_id": reply.session_id, "reply": reply.text,
                "tool_trace": reply.tool_trace}
    except Exception as exc:
        LOGGER.exception("Chat turn failed")
        return JSONResponse(
            status_code=500,
            content={
                "session_id": session_id,
                "error": "Chat turn failed. Check the server log for the traceback.",
                "error_type": type(exc).__name__,
                "detail": str(exc)[:500],
            },
        )


@app.post("/predict")
def predict(req: PredictRequest) -> Any:
    try:
        features = get_runtime().build_feature_row(
            req.home_team, req.away_team, neutral=req.neutral,
        )
        p = live_predict(features, req.home_team, req.away_team)
        return {**asdict(p), "features_used": len(features)}
    except Exception as exc:
        LOGGER.exception("Prediction failed")
        return JSONResponse(
            status_code=500,
            content={
                "error": "Prediction failed. Check the server log for the traceback.",
                "error_type": type(exc).__name__,
                "detail": str(exc)[:500],
            },
        )


@app.get("/memory/{session_id}")
def get_memory(session_id: str) -> dict[str, Any]:
    em = EpisodicMemory(session_id)
    turns = em.recent(limit=50)
    return {"turns": [
        {"role": t.role, "content": t.content,
         "tool_name": t.tool_name, "tool_args": t.tool_args}
        for t in turns
    ]}


@app.get("/observability/{session_id}")
def get_observability(session_id: str, limit: int = 100) -> dict[str, Any]:
    steps = list_steps(session_id, limit=limit)
    return {
        "session_id": session_id,
        "backend": "langgraph-oracledb.OracleStore",
        "steps": [
            {"key": step.key, **step.value}
            for step in steps
        ],
    }


@app.delete("/memory/{session_id}")
def clear_memory(session_id: str) -> dict[str, Any]:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM episodic_memory WHERE session_id = :sid",
                    sid=session_id)
        cur.execute("DELETE FROM working_memory WHERE session_id = :sid",
                    sid=session_id)
        conn.commit()
    return {"ok": True}


if STATIC_DIR.exists():
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
else:
    LOGGER.warning("No UI directory found at %s — the API runs but `/` serves nothing.", STATIC_DIR)
