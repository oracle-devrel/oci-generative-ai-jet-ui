"""Translate LangGraph `astream_events` into typed events for the UI.

The frontend cares about *what* is happening, not LangChain's internal
event taxonomy. We map raw events down to a stable, small surface:

    {"type": "agent_started", "agent": "demand_analyst"}
    {"type": "tool_started",  "agent": "policy_agent", "tool": "get_user_memory", "args": {...}}
    {"type": "tool_finished", "agent": "policy_agent", "tool": "get_user_memory", "result": "..."}
    {"type": "agent_finished","agent": "demand_analyst", "summary": "..."}
    {"type": "token",         "agent": "supervisor", "token": "Hello"}
    {"type": "final_answer",  "content": "..."}
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

# Known specialist names — used to identify which agent emitted an event.
KNOWN_AGENTS = {"supervisor", "demand_analyst", "policy_agent"}


def _agent_from_event(event: dict[str, Any]) -> str | None:
    """Best-effort: figure out which agent an event belongs to."""
    # LangGraph attaches a `metadata.langgraph_node` to most events.
    md = event.get("metadata") or {}
    node = md.get("langgraph_node")
    if node in KNOWN_AGENTS:
        return node
    # Sub-graphs nest; `metadata.langgraph_path` or `name` may carry it.
    name = event.get("name")
    if name in KNOWN_AGENTS:
        return name
    # Fall back to checkpoint_ns prefix
    ns = md.get("checkpoint_ns") or ""
    for known in KNOWN_AGENTS:
        if known in ns:
            return known
    return None


async def translate_events(
    raw: AsyncIterator[dict[str, Any]],
) -> AsyncIterator[dict[str, Any]]:
    """Map raw `astream_events` into the small frontend event surface."""
    last_final_content = ""

    async for ev in raw:
        et = ev.get("event")

        # Tokens from the chat model
        if et == "on_chat_model_stream":
            chunk = (ev.get("data") or {}).get("chunk")
            token = getattr(chunk, "content", "") if chunk is not None else ""
            if token:
                yield {
                    "type": "token",
                    "agent": _agent_from_event(ev) or "supervisor",
                    "token": token,
                }
            continue

        # Tools
        if et == "on_tool_start":
            yield {
                "type": "tool_started",
                "agent": _agent_from_event(ev),
                "tool": ev.get("name"),
                "args": (ev.get("data") or {}).get("input", {}),
            }
            continue
        if et == "on_tool_end":
            data = ev.get("data") or {}
            output = data.get("output")
            result = getattr(output, "content", None) or (str(output) if output is not None else "")
            yield {
                "type": "tool_finished",
                "agent": _agent_from_event(ev),
                "tool": ev.get("name"),
                "result": result[:4000],
            }
            continue

        # Agent / sub-graph lifecycle
        if et == "on_chain_start":
            name = ev.get("name")
            if name in KNOWN_AGENTS:
                yield {"type": "agent_started", "agent": name}
            continue
        if et == "on_chain_end":
            name = ev.get("name")
            if name in KNOWN_AGENTS:
                data = ev.get("data") or {}
                output = data.get("output")
                # Pull a short summary if available
                summary = ""
                if isinstance(output, dict):
                    msgs = output.get("messages") or []
                    if msgs:
                        last = msgs[-1]
                        summary = getattr(last, "content", "") or str(last)
                yield {
                    "type": "agent_finished",
                    "agent": name,
                    "summary": summary[:1000],
                }
            continue

    # Synthesise a final_answer signal so the UI knows when the stream
    # is genuinely over (some clients miss the implicit end-of-stream).
    yield {"type": "stream_end", "content": last_final_content}
