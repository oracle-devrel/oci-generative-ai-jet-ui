"""Oracle checkpointer durability round-trip test.

Verifies that LangGraph state written through one AsyncOracleSaver actually
persists in Oracle by reading it back through a second, independently-pooled
saver — proving the checkpoint lives in the DB, not in shared in-process state.

Skipped unless ``LANGGRAPH_CHECKPOINTER=oracle`` is set (in the shell or in
agent/.env) — requires a live Oracle DB with the env vars ``ORACLE_DB_USER``,
``ORACLE_DB_PASSWORD``, and ``ORACLE_DB_DSN`` present.
"""

from __future__ import annotations

import os
import uuid

import pytest
from dotenv import load_dotenv

# Load agent/.env BEFORE the skip is evaluated, so flipping LANGGRAPH_CHECKPOINTER
# in .env (the documented switch) actually enables this test. load_dotenv does not
# override an already-exported shell var, so an explicit `export` still wins.
load_dotenv()

# Module-level skip: entire file is skipped unless Oracle is selected.
pytestmark = pytest.mark.skipif(
    os.getenv("LANGGRAPH_CHECKPOINTER", "memory").lower() != "oracle",
    reason="requires LANGGRAPH_CHECKPOINTER=oracle + a live Oracle DB",
)


async def test_checkpoint_survives_fresh_saver() -> None:
    """State written through saver1 must be readable through saver2 (same DB).

    This proves durability: the checkpoint lives in Oracle, not in-process RAM.
    """
    import oracledb
    from langchain_core.messages import AIMessage, HumanMessage
    from langgraph.graph import END, START, MessagesState, StateGraph
    from langgraph_oracledb.checkpoint.oracle import AsyncOracleSaver

    def _require(name: str) -> str:
        value = os.getenv(name)
        if not value:
            raise RuntimeError(
                f"Missing required environment variable {name!r}. "
                "Copy agent/.env.example to agent/.env and fill it in."
            )
        return value

    user = _require("ORACLE_DB_USER")
    password = _require("ORACLE_DB_PASSWORD")
    dsn = _require("ORACLE_DB_DSN")

    # Unique per run (uuid, not a 1-second timestamp) so parallel/repeated runs
    # can't collide and read each other's rows (which would be a false green).
    thread_id = f"verify-{uuid.uuid4()}"
    config = {"configurable": {"thread_id": thread_id}}

    # ── Trivial graph definition (reused for both compilations) ──────────────
    def _build_graph(checkpointer):
        def probe_node(state: MessagesState):
            return {"messages": [AIMessage(content="durability-probe")]}

        sg = StateGraph(MessagesState)
        sg.add_node("probe", probe_node)
        sg.add_edge(START, "probe")
        sg.add_edge("probe", END)
        return sg.compile(checkpointer=checkpointer)

    pool1 = None
    pool2 = None
    try:
        # ── Phase 1: write a checkpoint via saver1 ───────────────────────────
        pool1 = oracledb.create_pool_async(
            user=user,
            password=password,
            dsn=dsn,
            min=1,
            max=4,
            increment=1,
        )
        saver1 = AsyncOracleSaver(pool1)
        await saver1.setup()

        graph1 = _build_graph(saver1)

        # Baseline: this brand-new thread has no checkpoint yet, so the Phase-2
        # read-back can only succeed if Phase 1's write actually persisted (rules
        # out a saver that merely echoes whatever was put in this run).
        baseline = await graph1.aget_state(config)
        assert not baseline.values.get(
            "messages"
        ), "thread unexpectedly already has state before the write"

        async for _ in graph1.astream(
            {"messages": [HumanMessage(content="hi")]}, config
        ):
            pass

        # ── Phase 2: read it back via saver2 (fresh saver, same DB) ─────────
        pool2 = oracledb.create_pool_async(
            user=user,
            password=password,
            dsn=dsn,
            min=1,
            max=4,
            increment=1,
        )
        saver2 = AsyncOracleSaver(pool2)
        # No setup() needed to read; tables already exist.

        graph2 = _build_graph(saver2)
        state = await graph2.aget_state(config)

        # Collect all message contents for assertion.
        messages = state.values.get("messages", [])
        contents = [getattr(m, "content", "") for m in messages]

        assert any(
            "durability-probe" in c for c in contents
        ), f"Expected 'durability-probe' in messages, got: {contents}"

        assert any(
            "hi" in c for c in contents
        ), f"Expected HumanMessage 'hi' in messages, got: {contents}"

        assert (
            len(messages) >= 2
        ), f"expected >=2 messages (human + ai), got {len(messages)}: {contents}"

        # Tidy up the checkpoint rows this run wrote so the shared DB doesn't
        # accumulate one verify-* thread per run.
        await saver2.adelete_thread(thread_id)

    finally:
        if pool1 is not None:
            await pool1.close()
        if pool2 is not None:
            await pool2.close()
