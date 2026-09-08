"""Build the structured payload the right-side Memory Context pane renders.

Each section is one collapsible card on the front-end. Sections are independent
and tolerate missing data — if a probe fails, that section is empty rather than
the whole pane breaking.

OAMP API (verified against installed package):
  - thread messages    → memory_client._store.list_thread_messages(thread_id, last_n=N) → list[MessageRecord(.role, .content, .timestamp, .metadata)]
  - semantic search    → memory_client.search(query, *, user_id, agent_id, max_results=N) → list[SearchResult(.id, .content, .record)]
  - memory list        → memory_client._store.list("memory", *, user_id, agent_id, thread_id, metadata_filter, limit) → list[MemoryRecord(.content, .metadata, .timestamp)]
"""

from __future__ import annotations

import traceback
from typing import Any

from agent.skills import build_skill_manifest
from agent.system_prompt import SYSTEM_PROMPT
from config import AGENT_ID, ONNX_EMBED_MODEL, USER_ID
from db.dbfs import DBFS


def _safe(callable_, default, *, label: str = ""):
    try:
        return callable_()
    except Exception as e:
        # Print to backend stdout so we can see what's actually breaking.
        print(f"[context] section {label!r} failed: {type(e).__name__}: {e}")
        if False:  # set True for full traceback when debugging
            traceback.print_exc()
        return default


def get_context_window(*, agent_conn, memory_client, thread_id: str, query: str) -> dict[str, Any]:
    """Snapshot of every input that *would* enter the context for this thread/query.

    Sections are thread-scoped where it matters: the scratchpad, tool outputs,
    episodic memories, and recent messages all come back filtered to
    `thread_id`. Top semantic memories stay globally retrievable (that's the
    point of institutional knowledge) but each row carries an
    `origin_thread_id` so the UI can flag which were first written on this
    thread vs. another / global.
    """
    sections = []

    sections.append({
        "key": "system_prompt",
        "name": "System prompt (live)",
        "items": _safe(lambda: _system_prompt_block(agent_conn, query),
                       [], label="system_prompt"),
    })

    sections.append({
        "key": "messages",
        "name": "Recent thread messages",
        "items": _safe(lambda: _list_thread_messages(memory_client, thread_id, limit=10),
                       [], label="messages"),
    })

    sections.append({
        "key": "memories",
        "name": "Top semantic memories",
        "items": _safe(lambda: _top_memories(memory_client, query, thread_id, k=6),
                       [], label="memories"),
    })

    sections.append({
        "key": "episodic",
        "name": "Episodic memories (this thread)",
        "items": _safe(lambda: _episodic_memories(memory_client, query, thread_id, k=5),
                       [], label="episodic"),
    })

    sections.append({
        "key": "tool_outputs",
        "name": "Recent tool outputs (this thread)",
        "items": _safe(lambda: _recent_tool_outputs(memory_client, thread_id, limit=8),
                       [], label="tool_outputs"),
    })

    sections.append({
        "key": "scratchpad",
        "name": "DBFS scratchpad (this thread)",
        "items": _safe(lambda: _scratchpad_files(agent_conn, thread_id),
                       [], label="scratchpad"),
    })

    sections.append({
        "key": "skill_manifest",
        "name": "Skill manifest",
        "items": _safe(lambda: _skill_manifest(agent_conn, query, k=3),
                       [], label="skill_manifest"),
    })

    sections.append({
        "key": "tool_manifest",
        "name": "Tool manifest",
        "items": _safe(lambda: _tool_manifest(agent_conn, query, k=6),
                       [], label="tool_manifest"),
    })

    return {"thread_id": thread_id, "query": query, "sections": sections}


def _system_prompt_block(agent_conn, query: str):
    """Show the actual system prompt + the skill manifest that gets prepended this turn."""
    manifest = ""
    try:
        manifest = build_skill_manifest(agent_conn, query, k=3) if query else ""
    except Exception:
        manifest = ""
    out = []
    if manifest:
        out.append({
            "label": "Skill manifest (prepended this turn)",
            "content": manifest.rstrip(),
        })
    out.append({
        "label": "SYSTEM_PROMPT",
        "content": SYSTEM_PROMPT,
    })
    return out


def _scratchpad_files(agent_conn, thread_id: str | None = None):
    """List the active thread's scratchpad files and preview their content.

    Files are physically located under `/scratch/threads/<thread_id>/...`
    (set by tool_scratch_write). Anything under `/scratch/threads/<other>/`
    is OUT — the right pane reflects only what THIS thread can see. We also
    surface the `display_path` (with the thread prefix stripped) so the UI
    can render the same name the agent uses (`findings.md` rather than the
    full physical path).

    Files outside `/scratch/threads/...` (legacy or operator-written) are
    shown when `thread_id` is None/empty so an operator can still inspect
    them via the explorer.
    """
    scratch = DBFS(agent_conn)
    try:
        paths = scratch.list("/")
    except Exception:
        return []

    prefix = f"/scratch/threads/{thread_id}/" if thread_id else None
    items = []
    for p in paths or []:
        in_scope = False
        display_path = p
        owning_thread = "shared"
        if p.startswith("/scratch/threads/"):
            rest = p[len("/scratch/threads/"):]
            owning_thread = rest.split("/", 1)[0] if "/" in rest else rest
            if prefix and p.startswith(prefix):
                in_scope = True
                display_path = p[len(prefix):]
            elif not prefix:
                # No active thread — show every thread's files but flag them.
                in_scope = True
        else:
            # Files outside /scratch/threads/* are pre-isolation legacy. Only
            # surface them when we have no active thread to compare against.
            in_scope = not prefix

        if not in_scope:
            continue

        try:
            content = scratch.read(p)
        except Exception as e:
            content = f"[unreadable: {type(e).__name__}: {e}]"
        items.append({
            "path": display_path,
            "full_path": p,
            "thread_id": owning_thread,
            "bytes": len(content) if isinstance(content, str) else 0,
            "preview": (content or "")[:600],
        })
    return items


def _episodic_memories(memory_client, query: str, thread_id: str | None = None, k: int = 5):
    """Search OAMP for memories tagged kind=episodic, scoped to the active thread.

    Episodic memories are the (user, assistant) pairs the harness writes after
    every turn. They're tagged with the thread they were written on. This pane
    section shows ONLY memories from `thread_id`; cross-thread retrieval still
    happens inside the agent loop via `search_knowledge`, but the right pane
    is meant to mirror exactly what THIS thread has accumulated so far.
    """
    if not query or not thread_id:
        return []
    raw = memory_client.search(
        query=query,
        user_id=USER_ID,
        agent_id=AGENT_ID,
        max_results=k * 4,
    )
    items = []
    for r in raw or []:
        rec = getattr(r, "record", None)
        meta = (getattr(rec, "metadata", None) if rec else None) or {}
        if meta.get("kind") != "episodic":
            continue
        # Hard scope: only episodes that originated on this thread.
        if str(meta.get("thread_id", "")) != str(thread_id):
            continue
        body = getattr(r, "content", "") or ""
        if hasattr(body, "read"):
            body = body.read()
        items.append({
            "thread_id": meta.get("thread_id", ""),
            "user_query": str(meta.get("user_query", ""))[:200],
            "body": str(body)[:600],
        })
        if len(items) >= k:
            break
    return items


def _list_thread_messages(memory_client, thread_id: str, limit: int = 10):
    """Pull the last N messages on this thread via OAMP's IMemoryStore.

    `last_n` is the keyword used by the underlying API; messages come back as
    `MessageRecord` dataclasses with `.role`, `.content`, `.timestamp`.
    """
    if not thread_id:
        return []
    rows = memory_client._store.list_thread_messages(thread_id, last_n=limit)
    out = []
    for m in rows or []:
        content = getattr(m, "content", "") or ""
        if hasattr(content, "read"):
            content = content.read()
        out.append({
            "role": getattr(m, "role", "?") or "?",
            "content": str(content)[:600],
        })
    return out


def _top_memories(memory_client, query: str, thread_id: str | None = None, k: int = 6):
    """Vector-search OAMP memories, filtering out tool_output and episodic kinds.

    Top semantic memories are intentionally GLOBAL — institutional knowledge
    (table/column/relationship/correction facts) should be retrievable from
    any thread; that's the whole point of `tool_remember`. But we tag every
    row's provenance so the UI can flag whether a hit was first written on
    THIS thread, on a different thread, or has no thread origin (scanner
    facts written by `scan_database`).
    """
    if not query:
        return []
    raw = memory_client.search(
        query=query,
        user_id=USER_ID,
        agent_id=AGENT_ID,
        max_results=k * 3,
    )
    items = []
    for r in raw or []:
        rec = getattr(r, "record", None)
        meta = (getattr(rec, "metadata", None) if rec else None) or {}
        kind = meta.get("kind", "memory")
        # Episodic memories live in their own pane section; tool outputs in
        # theirs. Don't double-render here.
        if kind in ("tool_output", "episodic"):
            continue
        body = getattr(r, "content", "") or ""
        if hasattr(body, "read"):
            body = body.read()
        origin = str(meta.get("origin_thread_id") or meta.get("thread_id") or "")
        if not origin:
            scope = "global"
        elif thread_id and origin == thread_id:
            scope = "this_thread"
        else:
            scope = "other_thread"
        items.append({
            "kind": kind,
            "subject": meta.get("subject", ""),
            "body": str(body)[:500],
            "origin_thread_id": origin,
            "scope": scope,
        })
        if len(items) >= k:
            break
    return items


def _recent_tool_outputs(memory_client, thread_id: str, limit: int = 8):
    """List recent tool_output memories on this thread (in OAMP, by metadata kind)."""
    if not thread_id:
        return []
    rows = memory_client._store.list(
        "memory",
        user_id=USER_ID,
        agent_id=AGENT_ID,
        thread_id=thread_id,
        metadata_filter={"kind": "tool_output"},
        limit=limit,
    )
    out = []
    for r in rows or []:
        meta = getattr(r, "metadata", None) or {}
        body = getattr(r, "content", "") or ""
        if hasattr(body, "read"):
            body = body.read()
        out.append({
            "tool_name": meta.get("tool_name", "?"),
            "tool_call_id": meta.get("tool_call_id", ""),
            "args": str(meta.get("tool_args", ""))[:240],
            "preview": str(body)[:600],
        })
    return out


def _skill_manifest(agent_conn, query: str, k: int = 3):
    if not query:
        return []
    with agent_conn.cursor() as cur:
        cur.execute(
            "SELECT name, category, description FROM skillbox "
            f" ORDER BY VECTOR_DISTANCE(embedding, VECTOR_EMBEDDING({ONNX_EMBED_MODEL} USING :q AS DATA), COSINE) "
            " FETCH FIRST :k ROWS ONLY",
            q=query, k=k,
        )
        rows = list(cur)
    return [
        {
            "name": n,
            "category": c,
            "description": (d.read() if hasattr(d, "read") else d)[:300],
        }
        for n, c, d in rows
    ]


def _tool_manifest(agent_conn, query: str, k: int = 6):
    if not query:
        return []
    with agent_conn.cursor() as cur:
        cur.execute(
            "SELECT name, description FROM toolbox "
            f" ORDER BY VECTOR_DISTANCE(embedding, VECTOR_EMBEDDING({ONNX_EMBED_MODEL} USING :q AS DATA), COSINE) "
            " FETCH FIRST :k ROWS ONLY",
            q=query, k=k,
        )
        rows = list(cur)
    return [
        {
            "name": n,
            "description": (d.read() if hasattr(d, "read") else d)[:300],
        }
        for n, d in rows
    ]


def list_threads(memory_client, limit: int = 50, agent_conn=None) -> list[dict]:
    """List threads for the left nav.

    OAMP's `_store.list("thread", ...)` raises `ValueError: Unsupported DB
    record_type` — its `_resolve_record_table` only handles `message` and
    memory-table types. Threads have to be queried directly against the OAMP
    thread table (`{table_name_prefix}thread`, lowercase, singular).
    """
    if agent_conn is None:
        # Fall back to the OAMP connection if no explicit agent_conn was passed.
        agent_conn = getattr(memory_client._store, "_conn", None)
    if agent_conn is None:
        print("[context] list_threads: no connection available")
        return []

    table_name = "eda_onnx_thread"  # matches table_name_prefix='eda_onnx_' in memory/manager.py
    try:
        with agent_conn.cursor() as cur:
            cur.execute(
                f"SELECT record_id, created_at, metadata "
                f"  FROM {table_name} "
                f" WHERE user_id = :u AND agent_id = :a "
                f" ORDER BY created_at DESC "
                f" FETCH FIRST :n ROWS ONLY",
                u=USER_ID, a=AGENT_ID, n=limit,
            )
            rows = list(cur)
    except Exception as e:
        print(f"[context] list_threads SQL failed: {type(e).__name__}: {e}")
        return []

    out = []
    for record_id, created_at, metadata in rows:
        meta = metadata or {}
        if hasattr(metadata, "read"):
            try:
                import json as _json
                meta = _json.loads(metadata.read()) or {}
            except Exception:
                meta = {}
        out.append({
            "thread_id": record_id,
            "created_at": str(created_at) if created_at else "",
            "summary": str((meta or {}).get("summary", ""))[:200],
        })
    return out
