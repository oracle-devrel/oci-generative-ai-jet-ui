"""LangGraph OracleDB-backed observability for agent execution steps.

The app is intentionally not a LangGraph runtime: OCI Grok bearer auth does not
expose native tool-calling, so the agent uses a small prompt-protocol loop. We
still use the official ``langgraph-oracledb`` package as the durable Oracle
backend for observability records. Each step is an ``OracleStore`` item scoped by
session, which makes the model/tool flow inspectable after the turn completes.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from functools import lru_cache
from typing import Any
from uuid import uuid4

from langgraph_oracledb.store.oracle import OracleStore

from soccer_agent.db import get_connection

NAMESPACE_ROOT = ("soccer-agent", "agent-steps")


class LangGraphObservabilityUnavailable(RuntimeError):
    """Raised when the LangGraph OracleDB observability store is unavailable."""


@dataclass(frozen=True)
class ObservabilityStep:
    """One durable agent-step record stored in LangGraph OracleStore."""

    key: str
    value: dict[str, Any]


def new_turn_id() -> str:
    """Create a stable id for all step records belonging to one chat turn."""
    return f"turn-{uuid4()}"


def namespace_for(session_id: str) -> tuple[str, ...]:
    """Return the OracleStore namespace for one agent session."""
    return (*NAMESPACE_ROOT, session_id)


def _json_safe(value: Any) -> Any:
    """Convert common non-JSON values into OracleStore-friendly structures."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(v) for v in value]
    if hasattr(value, "read"):
        return _json_safe(value.read())
    return str(value)


@lru_cache(maxsize=1)
def ensure_observability_store() -> None:
    """Create/upgrade LangGraph OracleStore tables once per process."""
    try:
        with get_connection() as conn:
            OracleStore(conn).setup()
    except Exception as exc:  # pragma: no cover - exact DB errors are environment-specific
        raise LangGraphObservabilityUnavailable(
            f"langgraph-oracledb OracleStore setup failed: {exc}"
        ) from exc


def record_step(
    *,
    session_id: str,
    turn_id: str,
    step_index: int,
    event_type: str,
    payload: dict[str, Any] | None = None,
    tool_name: str | None = None,
) -> str:
    """Persist one agent execution step via langgraph-oracledb OracleStore.

    Returns the OracleStore key. Observability writes are intentionally isolated
    from chat correctness: callers may catch ``LangGraphObservabilityUnavailable``
    and continue serving the turn if the package or store is temporarily down.
    """
    ensure_observability_store()
    key = f"{turn_id}:{step_index:04d}:{event_type}"
    value = {
        "session_id": session_id,
        "turn_id": turn_id,
        "step_index": int(step_index),
        "event_type": event_type,
        "tool_name": tool_name,
        "created_at": datetime.now(UTC).isoformat(),
        "payload": _json_safe(payload or {}),
        "observability_backend": "langgraph-oracledb.OracleStore",
    }
    try:
        with get_connection() as conn:
            store = OracleStore(conn)
            store.setup()
            store.put(namespace_for(session_id), key, value)
            conn.commit()
    except Exception as exc:  # pragma: no cover - exact DB errors are environment-specific
        raise LangGraphObservabilityUnavailable(
            f"langgraph-oracledb OracleStore write failed: {exc}"
        ) from exc
    return key


def list_steps(session_id: str, *, limit: int = 100) -> list[ObservabilityStep]:
    """Read stored agent steps for one session from LangGraph OracleStore."""
    ensure_observability_store()
    try:
        with get_connection() as conn:
            store = OracleStore(conn)
            store.setup()
            items = store.search(namespace_for(session_id), limit=limit)
    except Exception as exc:  # pragma: no cover - exact DB errors are environment-specific
        raise LangGraphObservabilityUnavailable(
            f"langgraph-oracledb OracleStore read failed: {exc}"
        ) from exc

    steps = [
        ObservabilityStep(key=item.key, value=dict(item.value))
        for item in items
    ]
    return sorted(steps, key=lambda s: (s.value.get("turn_id", ""), s.value.get("step_index", 0), s.key))
