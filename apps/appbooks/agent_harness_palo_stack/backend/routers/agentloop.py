"""Layer 7 — The Agent Loop, and Layer 8 — Context Engineering."""
from __future__ import annotations

from fastapi import APIRouter

from backend.core import agent
from backend.core.sse import sse_response
from backend.schemas import AgentReq

router = APIRouter(prefix="/api", tags=["agent"])


@router.post("/agent/run")
async def run(req: AgentReq):
    return sse_response(agent.run_agent(req.prompt, req.thread_id))


@router.get("/context/series")
def context_series(turns: int = 16, card_size: int = 900, tool_blob: int = 3600) -> dict:
    """The 'money shot' series: context size per turn, engineering OFF vs ON."""

    def sim(engineering: bool):
        sizes, hist = [], []
        for _ in range(turns):
            hist += [40, (80 if engineering else tool_blob), 60]  # user, tool result, assistant
            convo = card_size if engineering else sum(hist)
            sizes.append(convo + (sum(hist[-2:]) if engineering else 0))
        return sizes

    return {"off": sim(False), "on": sim(True)}
