"""REST endpoints. The Socket.IO surface in events.py is the primary path
for chat traffic; these routes are for thread management and synchronous
context fetches the front-end uses on initial load."""

from __future__ import annotations

from flask import Blueprint, jsonify, request

from api.context import get_context_window, list_threads


api_bp = Blueprint("api", __name__)


_state: dict = {}


def init_routes(*, agent_conn, memory_client, llm_client):
    _state.update(
        agent_conn=agent_conn,
        memory_client=memory_client,
        llm_client=llm_client,
    )


@api_bp.route("/api/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "components": {
            "oracle": _state.get("agent_conn") is not None,
            "memory": _state.get("memory_client") is not None,
            "llm": _state.get("llm_client") is not None,
        },
    })


@api_bp.route("/api/threads", methods=["GET"])
def threads():
    rows = list_threads(
        _state["memory_client"],
        limit=int(request.args.get("limit", "50")),
        agent_conn=_state.get("agent_conn"),
    )
    return jsonify({"threads": rows})


@api_bp.route("/api/threads/<thread_id>/messages", methods=["GET"])
def thread_messages(thread_id: str):
    """Return the last N messages on a thread (for restoring chat history when
    the user clicks an existing thread in the left nav)."""
    mc = _state.get("memory_client")
    if not mc:
        return jsonify({"error": "not initialized"}), 503
    try:
        rows = mc._store.list_thread_messages(
            thread_id, last_n=int(request.args.get("limit", "100")),
        )
    except Exception as e:
        return jsonify({"error": f"{type(e).__name__}: {e}"}), 500
    out = []
    for m in rows or []:
        content = getattr(m, "content", "") or ""
        if hasattr(content, "read"):
            content = content.read()
        out.append({
            "role": getattr(m, "role", "?") or "?",
            "content": str(content),
            "timestamp": str(getattr(m, "timestamp", "")),
        })
    return jsonify({"thread_id": thread_id, "messages": out})


@api_bp.route("/api/threads/<thread_id>", methods=["DELETE"])
def delete_thread(thread_id: str):
    """Delete a thread and all of its messages + memories. The OAMP client
    cascades deletes through the store, so this single call removes both."""
    mc = _state.get("memory_client")
    if not mc:
        return jsonify({"error": "not initialized"}), 503
    try:
        mc.delete_thread(thread_id)
        return jsonify({"ok": True, "thread_id": thread_id})
    except Exception as e:
        return jsonify({"error": f"{type(e).__name__}: {e}"}), 500


@api_bp.route("/api/context/<thread_id>", methods=["GET"])
def context(thread_id: str):
    query = request.args.get("query", "")
    payload = get_context_window(
        agent_conn=_state["agent_conn"],
        memory_client=_state["memory_client"],
        thread_id=thread_id,
        query=query,
    )
    return jsonify(payload)
