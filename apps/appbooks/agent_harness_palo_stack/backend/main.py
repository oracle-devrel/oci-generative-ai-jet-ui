"""Total Recall appbook — FastAPI application.

Warms the harness (connects to the AGENT schema, creates anything missing
idempotently) in the background on startup, mounts one router group per layer,
and serves the dependency-free SPA from the same origin.

Run from the appbook/ directory:
    uvicorn backend.main:app --reload --port 8000
"""
from __future__ import annotations

import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.config import FRONTEND_DIR
from backend.core import db
from backend.routers import agentloop, automations, layers, memory, skills


def _warm():
    try:
        db.initialize()
    except Exception:
        pass  # status() records the error; the frontend still serves with a badge


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Warm the harness without blocking startup (so the frontend serves immediately).
    threading.Thread(target=_warm, daemon=True).start()
    yield


app = FastAPI(title="Total Recall — Appbook", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

for r in (layers.router, memory.router, skills.router, agentloop.router, automations.router):
    app.include_router(r)

app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=False)
