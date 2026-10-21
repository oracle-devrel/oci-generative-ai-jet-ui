"""OAMP-backed memory layer. Mirrors §4.1 of the notebook: the OracleAgentMemory
client owns memories/threads/context-cards; we add a custom in-DB ONNX embedder.

The whole agent reads/writes memory through this module so the API surface is
small and stable.

OAMP 26.8 adds database-native Deep Data Security for this store
(`oracleagentmemory.core.deepsec`): `db/deep_security.py` installs the
UserOwnRows + GlobalMemories policies on a Deep Sec-capable database and
`docs/reference/deep-data-security.md` walks through the runtime context.
"""

from __future__ import annotations

import functools
import inspect
import threading

import numpy as np

from oracleagentmemory.core import OracleAgentMemory
from oracleagentmemory.core.thread import BaseThread
from oracleagentmemory.apis.embedders.embedder import IEmbedder

from config import (
    AGENT_ID, USER_ID,
    ONNX_EMBED_DIM, ONNX_EMBED_MODEL,
)
from oci_key_rotation import make_router_oamp_llm
from db.connection import create_agent_pool

# OAMP >= 26.6 names the managed DB objects from `memory_store_id`; the older
# `table_name_prefix` is deprecated and removed in 27.1. "EDA_ONNX" resolves to
# the same EDA_ONNX_MEMORY / EDA_ONNX_THREAD / ... tables the workshop has used
# since 26.4 — the store ID is joined to object names with an underscore.
MEMORY_STORE_ID = "EDA_ONNX"


def content_to_text(content) -> str:
    """Flatten an OAMP content value into plain text.

    OAMP >= 26.8 stores message/memory content as either a plain string or a
    sequence of ``MessageContent`` parts (``TextContent``, ``ImageContent``,
    ...). Calling ``str()`` on that sequence yields the dataclass repr — e.g.
    ``(TextContent(id='...', timestamp=None, text='...'),)`` — which is what the
    chat history and context pane used to render. This collapses it back to the
    underlying text so every read path returns a string.

    Also tolerates legacy values: raw strings, LOB objects (``.read()``), a
    single content part, and ``None``.
    """
    if content is None:
        return ""

    # Legacy LOB column / file-like value.
    if hasattr(content, "read"):
        try:
            content = content.read()
        except Exception:
            return str(content)

    if isinstance(content, str):
        return content

    # A single content part (TextContent / ImageContent / ...).
    if not isinstance(content, (list, tuple)):
        text = getattr(content, "text", None)
        if isinstance(text, str):
            return text
        if hasattr(content, "description"):
            desc = getattr(content, "description", None)
            return f"[image: {desc}]" if desc else "[image]"
        return str(content)

    # A sequence of content parts.
    parts: list[str] = []
    for part in content:
        if part is None:
            continue
        if isinstance(part, str):
            parts.append(part)
            continue
        text = getattr(part, "text", None)
        if isinstance(text, str):
            parts.append(text)
            continue
        if hasattr(part, "description"):
            desc = getattr(part, "description", None)
            parts.append(f"[image: {desc}]" if desc else "[image]")
            continue
        parts.append(str(part))
    return "\n".join(p for p in parts if p)


class OracleONNXEmbedder(IEmbedder):
    """Routes embedding through Oracle's in-DB ONNX model (§3.4 of the notebook).
    Same database the OAMP client uses → no network round-trip, no extra keys.

    `conn` is a connection or a connection pool (OAMP's background extraction
    worker embeds from its own thread, so the app hands it the pool).
    """

    def __init__(self, conn, model_name: str = ONNX_EMBED_MODEL, dim: int = ONNX_EMBED_DIM):
        self._conn = conn
        self._model = model_name
        self._dim = dim

    def embed(self, texts: list[str], *, is_query: bool = False) -> np.ndarray:
        out = np.zeros((len(texts), self._dim), dtype=np.float32)
        sql = f"SELECT VECTOR_EMBEDDING({self._model} USING :t AS DATA) FROM dual"
        pooled = hasattr(self._conn, "acquire")
        conn = self._conn.acquire() if pooled else self._conn
        try:
            with conn.cursor() as cur:
                for i, t in enumerate(texts):
                    cur.execute(sql, t=t)
                    vec = cur.fetchone()[0]
                    out[i] = np.asarray(list(vec), dtype=np.float32)
        finally:
            if pooled:
                conn.close()
        return out

    async def embed_async(self, texts: list[str], *, is_query: bool = False) -> np.ndarray:
        return self.embed(texts, is_query=is_query)


def build_extraction_llm():
    """LLM used by OAMP for memory extraction + context-summary refresh.

    Routed through the app-wide ModelRouter (same cooldown state as chat).
    Returns None if no lane is configured — caller disables extraction.
    """
    from agent.llm import get_router
    try:
        llm = make_router_oamp_llm(get_router())
    except Exception as e:
        print(f"[memory] No usable LLM — OAMP extraction DISABLED ({type(e).__name__}).")
        return None
    print("[memory] OAMP extraction LLM = shared model router")
    return llm


# --------------------------------------------------------------------------- #
# Thread safety
# --------------------------------------------------------------------------- #
# The app runs on real OS threads (Flask-SocketIO `threading` mode): chat turns,
# REST handlers, the scheduler drain loop and the AML recall all call OAMP. OAMP
# is not safe for that — one store per client, and its sync API spins up an
# asyncio loop per call. So every call into it goes through ONE app-wide
# re-entrant lock (the same rule as the notebook's `_OAMP_LOCK`), applied
# centrally by `_Locked` below instead of at each call site.
#
# OAMP's own background extraction / summary worker runs on its own thread
# *outside* this lock, so it must not share a database session with the
# foreground calls: the client sits on its own connection pool (see
# `build_memory_client`), never on the app's shared AGENT connection.
OAMP_LOCK = threading.RLock()


class _Locked:
    """Transparent proxy that runs every method of the wrapped OAMP object under
    `OAMP_LOCK`. Thread objects handed back by `get_thread`/`create_thread` are
    wrapped the same way, and so is the `_store` the app reaches into directly.
    Plain data (records, search results, ids) passes through unwrapped.

    The lock is held for the duration of one OAMP call only. Callers must never
    wrap an LLM chat call of their own in it.
    """

    __slots__ = ("_target",)

    def __init__(self, target):
        object.__setattr__(self, "_target", target)

    def __getattr__(self, name):
        attr = getattr(self._target, name)
        if name == "_store":
            return _Locked(attr)
        if not callable(attr) or inspect.iscoroutinefunction(attr):
            return attr

        @functools.wraps(attr)
        def locked_call(*args, **kwargs):
            with OAMP_LOCK:
                result = attr(*args, **kwargs)
            return _Locked(result) if isinstance(result, BaseThread) else result

        return locked_call

    def __setattr__(self, name, value):
        setattr(self._target, name, value)

    def __repr__(self):
        return f"<_Locked {self._target!r}>"


def build_memory_client() -> OracleAgentMemory:
    """The single OAMP client used by the loop and the API (lock-wrapped).

    If no LLM is available we still build the client (for memory storage and
    semantic retrieval), but disable auto-extraction so OAMP doesn't hit a
    None LLM during add_messages.
    """
    extraction_llm = build_extraction_llm()
    pool = create_agent_pool(min=1, max=4)
    client = OracleAgentMemory(
        connection=pool,
        embedder=OracleONNXEmbedder(pool),
        llm=extraction_llm,
        extract_memories=(extraction_llm is not None),
        schema_policy="create_if_necessary",
        memory_store_id=MEMORY_STORE_ID,
    )
    client = _Locked(client)
    for register_fn, eid, info in [
        (client.add_user, USER_ID, "Operator querying the enterprise database in natural language."),
        (client.add_agent, AGENT_ID, "Data agent grounded in scanned schema metadata."),
    ]:
        try:
            register_fn(eid, info)
        except ValueError as e:
            if "already exists" not in str(e):
                raise
    return client


def get_or_create_thread(client: OracleAgentMemory, thread_id: str):
    """Return the OAMP thread for a harness-level id, creating it on first use."""
    with OAMP_LOCK:  # get-then-create must be atomic across request threads
        try:
            return client.get_thread(thread_id)
        except Exception:
            return client.create_thread(
                thread_id=thread_id,
                user_id=USER_ID,
                agent_id=AGENT_ID,
                enable_context_summary=True,
            )


# --------------------------------------------------------------------------- #
# Memory relations (OAMP >= 26.8)
# --------------------------------------------------------------------------- #
# A relation is a directed edge between two stored memories. The type decides
# what OAMP's lifecycle engine does to the *target* memory, which is the part
# that surprises people:
#
#   supersedes   target -> INVALID  ("Superseded by another memory.")
#   refines      target -> INVALID  ("Refined by another memory.")
#   duplicates   target -> INVALID  ("Duplicated by another memory.")
#   contradicts  both stay VALID    (the conflict is the point)
#   supports     both stay VALID    (evidence, not replacement)
#
# Default searches hide INVALID memories; link traversal still returns them, so
# `search(..., num_hops=1)` is how history stays reachable after a correction.

LINK_TYPES = ("supersedes", "contradicts", "refines", "supports", "duplicates")
INVALIDATING_LINK_TYPES = ("supersedes", "refines", "duplicates")


def link_memories(
    client: OracleAgentMemory,
    source_id: str,
    target_id: str,
    link_type: str = "supersedes",
    metadata: dict | None = None,
) -> str | None:
    """Create one directed relation `source -link_type-> target`.

    Returns the relation id. OAMP stores one orientation per endpoint pair, so
    re-creating an existing relation returns its id instead of raising. For the
    invalidating types above, this also retires the target memory.
    """
    if link_type not in LINK_TYPES:
        raise ValueError(f"link_type must be one of {LINK_TYPES}, got {link_type!r}")
    store = client._store
    try:
        ids = store.add_relations(
            source_record_ids=source_id,
            source_record_types="memory",
            target_record_ids=target_id,
            target_record_types="memory",
            relation_types=link_type,
            metadata=metadata or {},
        )
        return ids[0] if ids else None
    except Exception as e:
        # Most likely the pair already has this relation (one orientation per
        # endpoint pair). Confirm that before reporting a failure.
        try:
            existing = store.get_relation(
                source_id, "memory", target_id, "memory", link_type
            )
            if existing is not None:
                return existing.id
        except Exception:
            pass
        print(
            f"[memory] link {str(source_id)[:8]} -{link_type}-> "
            f"{str(target_id)[:8]} failed: {type(e).__name__}: {e}"
        )
        return None


def find_memory(client: OracleAgentMemory, ref: str):
    """Resolve a memory id or a free-text phrase to one memory record.

    Exact ids are looked up directly; anything else is semantically searched
    with the same scope the agent's knowledge retrieval uses, valid memories
    only. Returns a MemoryRecord or None.
    """
    ref = (ref or "").strip()
    if not ref:
        return None
    if len(ref) >= 32 and "-" in ref:
        try:
            record = client._store.get("memory", ref)
            if record is not None:
                return record
        except Exception:
            pass
    hits = client.search(
        query=ref,
        user_id=USER_ID,
        agent_id=AGENT_ID,
        max_results=1,
        include_invalid_results=False,
    )
    if not hits:
        return None
    return getattr(hits[0], "record", None)


def _link_view(store, other_id: str, relation: str, direction: str) -> dict:
    """The far end of a relation, rendered for the tool/pane output."""
    record = None
    try:
        record = store.get("memory", other_id)
    except Exception:
        pass
    meta = (getattr(record, "metadata", None) or {}) if record else {}
    body = getattr(record, "content", "") if record else ""
    body = content_to_text(body)
    return {
        "relation": relation,
        "direction": direction,
        "memory_id": other_id,
        "kind": meta.get("kind", "memory"),
        "subject": meta.get("subject", ""),
        "status": str(getattr(record, "status", "")).split(".")[-1],
        "body": body[:300],
    }


def memory_links(
    client: OracleAgentMemory, memory_id: str, limit: int = 10
) -> list[dict]:
    """Relations touching a memory, normalised so the label reads from here.

    A memory that supersedes another reports `relation='supersedes'`,
    `direction='out'`; the superseded one reports `relation='is_superseded_by'`,
    `direction='in'`. Traversal follows links in either direction, matching
    `search(..., num_hops=N)`.
    """
    store = client._store
    out: list[dict] = []
    try:
        outgoing = store.list_relations(source_record_id=memory_id, limit=limit) or []
    except Exception:
        outgoing = []
    try:
        incoming = store.list_relations(target_record_id=memory_id, limit=limit) or []
    except Exception:
        incoming = []
    for rel in outgoing:
        out.append(_link_view(store, rel.target_record_id, rel.relation_type, "out"))
    for rel in incoming:
        label = rel.opposite_relation_type or rel.relation_type
        out.append(_link_view(store, rel.source_record_id, label, "in"))
    return out[:limit]
