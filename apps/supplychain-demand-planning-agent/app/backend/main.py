"""FastAPI entry point for the supply-chain demand-planning chat app."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from app.backend.api.data import router as data_router
from app.backend.api.websocket import chat_websocket
from app.backend.config import SETTINGS
from app.backend.db.connections import close_all
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
log = logging.getLogger("app.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("backend starting (settings=%s)", SETTINGS.public())
    yield
    log.info("backend shutting down, closing oracle connections …")
    await close_all()


app = FastAPI(title="Supply-chain demand-planning multi-agent chat", lifespan=lifespan)

# Frontend runs on :3000 in dev; allow it through.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health() -> JSONResponse:
    return JSONResponse({"status": "ok", **SETTINGS.public()})


@app.get("/api/agents")
async def agents() -> JSONResponse:
    """Static metadata about the multi-agent architecture — drives the
    architecture explorer's node graph in the UI."""
    return JSONResponse(
        {
            "nodes": [
                {"id": "user", "label": "Planner", "kind": "user"},
                {"id": "supervisor", "label": "Supervisor", "kind": "supervisor"},
                {"id": "demand_analyst", "label": "demand_analyst", "kind": "specialist"},
                {"id": "policy_agent", "label": "policy_agent", "kind": "specialist"},
                {"id": "oracle_vs", "label": "OracleVS", "kind": "store"},
                {"id": "agent_store", "label": "AsyncOracleStore", "kind": "store"},
                {"id": "saver", "label": "AsyncOracleSaver", "kind": "store"},
            ],
            "edges": [
                {"id": "user-sup", "source": "user", "target": "supervisor"},
                {"id": "sup-da", "source": "supervisor", "target": "demand_analyst"},
                {"id": "sup-pa", "source": "supervisor", "target": "policy_agent"},
                {
                    "id": "da-vs",
                    "source": "demand_analyst",
                    "target": "oracle_vs",
                    "label": "search_demand_reports",
                },
                {
                    "id": "pa-vs",
                    "source": "policy_agent",
                    "target": "oracle_vs",
                    "label": "get_planner_policy",
                },
                {
                    "id": "pa-store",
                    "source": "policy_agent",
                    "target": "agent_store",
                    "label": "get_user_memory",
                },
                {
                    "id": "sup-saver",
                    "source": "supervisor",
                    "target": "saver",
                    "label": "checkpoint",
                    "dashed": True,
                },
            ],
        }
    )


app.include_router(data_router)


@app.websocket("/ws/chat")
async def chat(ws: WebSocket) -> None:
    await chat_websocket(ws)
