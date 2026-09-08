"""Layer 4 — Cognitive memory (OAMP). A chat that remembers across turns and
sessions, with the OAMP context card shown live."""
from __future__ import annotations

import asyncio

from fastapi import APIRouter
from fastapi.concurrency import run_in_threadpool

from backend.core import memory
from backend.core.anthropic_client import MAX_TOKENS, MODEL, async_client
from backend.core.sse import sse_response
from backend.schemas import ChatReq, FactReq, ToolQuery

router = APIRouter(prefix="/api/memory", tags=["memory"])


@router.post("/chat")
async def chat(req: ChatReq):
    await run_in_threadpool(memory.add_turn, req.thread_id, "user", req.message)
    card = await run_in_threadpool(memory.context_card, req.thread_id) or ""
    system = (
        "You are a concise analytics assistant. The block below is your working memory "
        "(a rolling summary, relevant durable memories, and recent turns) — use it to stay "
        "consistent across turns.\n\n# WORKING MEMORY (OAMP context card)\n" + card
    )

    async def events():
        parts = []
        async with async_client.messages.stream(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=system,
            messages=[{"role": "user", "content": req.message}],
        ) as stream:
            async for text in stream.text_stream:
                parts.append(text)
                yield {"type": "delta", "text": text}
        reply = "".join(parts)
        await asyncio.to_thread(memory.add_turn, req.thread_id, "assistant", reply)
        new_card = await asyncio.to_thread(memory.context_card, req.thread_id) or ""
        yield {"type": "done", "card": new_card}

    return sse_response(events())


@router.get("/card")
async def card(thread_id: str = "appbook") -> dict:
    return {"card": await run_in_threadpool(memory.context_card, thread_id) or ""}


@router.post("/remember")
async def remember(req: FactReq) -> dict:
    mid = await run_in_threadpool(memory.remember, req.fact)
    return {"id": mid}


@router.post("/recall")
async def recall(req: ToolQuery) -> dict:
    return {"hits": await run_in_threadpool(memory.recall, req.query, 5)}


@router.get("/turns")
async def turns(thread_id: str = "appbook") -> dict:
    return {"turns": await run_in_threadpool(memory.get_turns, thread_id)}


@router.get("/threads")
async def threads(prefix: str = "mc-") -> dict:
    return {"threads": await run_in_threadpool(memory.list_threads, prefix)}


@router.get("/thread")
async def thread(thread_id: str) -> dict:
    return {"messages": await run_in_threadpool(memory.thread_messages, thread_id)}
