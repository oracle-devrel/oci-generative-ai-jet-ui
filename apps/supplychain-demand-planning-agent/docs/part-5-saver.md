# Part 5 — `AsyncOracleSaver` — per-thread checkpoints

## What a checkpointer does

`AsyncOracleSaver` is LangGraph's checkpointer for Oracle. It snapshots
**every step** of the agent graph (incoming messages, intermediate tool
outputs, the supervisor's internal state) into Oracle, keyed by
`thread_id`.

The agent is given a `thread_id` on every invocation:

```python
result = await supervisor.ainvoke(
    {"messages": [{"role": "user", "content": "..."}]},
    config={"configurable": {"thread_id": "demand-plan-soccer-2026Q3"}},
)
```

- **Re-invoking with the same `thread_id`** resumes from the last
  checkpoint. The supervisor sees the previous turn's messages and
  state and continues the conversation.
- **Invoking with a fresh `thread_id`** starts clean. No prior context.

This is the **short-term memory** — the conversation timeline, scoped
to one thread.

## Saver vs Store — pick the right primitive

| When you want…                                       | Use                                                                      |
| ---------------------------------------------------- | ------------------------------------------------------------------------ |
| Resume a paused conversation                         | **saver** (this part)                                                    |
| Remember the user's preferences across conversations | **store** (Part 4)                                                       |
| Both                                                 | compile with **both**: `.compile(checkpointer=saver, store=agent_store)` |

The supervisor in Part 10 compiles with both, which is the whole point
of the architecture.

## What gets checkpointed

Every node in the LangGraph state graph emits state on each step. The
saver writes:

- The full message history (user + assistant + tool messages)
- Intermediate state of each agent (the supervisor's plan, each
  specialist's tool calls and results)
- Channel writes (LangGraph's pub/sub between nodes)

`AsyncOracleSaver` packs all of that into a small set of tables
(`CHECKPOINTS`, `CHECKPOINT_WRITES`, `CHECKPOINT_BLOBS`,
`CHECKPOINT_MIGRATIONS`) and stores everything as Oracle JSON +
BLOB columns. The schema is created by `await saver.setup()` (also
idempotent).

## Construction

```python
saver = AsyncOracleSaver(saver_conn)
await saver.setup()
```

That's it — no index config, no `table_suffix`. There's only one
checkpoint table set per Oracle schema.

## What you'll build in TODO 4

Construct `saver` and call `await saver.setup()`. The hard-stop
checkpoint asks the saver to list its threads (even an empty list
counts as a successful smoke-test) — that round-trip proves the
checkpoint tables exist and are writable.

## Solution

Drop this into the TODO 4 cell, replacing the `saver = None` line:

```python
from langgraph_oracledb.checkpoint.oracle import AsyncOracleSaver

saver = AsyncOracleSaver(saver_conn)
await saver.setup()
```

## Why this matters for the workshop

The supervisor in Part 10 compiles with `checkpointer=saver`. The
moment you `.ainvoke(...)`, every step of the multi-agent graph starts
landing in Oracle as it runs. If the process dies mid-turn you can
resume right where it stopped.

The chat app in `app/` exercises this directly: every WebSocket session
opens a fresh `thread_id`, and every message you send accumulates into
that thread's checkpointed history.

## Next

→ **[Part 6 — `OracleSemanticCache`](part-6-cache.md)** — caching LLM responses, also in Oracle.
