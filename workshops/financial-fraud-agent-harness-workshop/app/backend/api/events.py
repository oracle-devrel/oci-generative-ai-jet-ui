"""Socket.IO event handlers. The chat path lives here so individual tool calls
can stream to the front-end as they happen.

Events the client emits:
  - send_message {thread_id, content}  → runs the loop, streams tool events,
                                          emits turn_finished with final answer
  - new_thread   {}                    → creates a new thread_id, returns it
  - request_context_window {thread_id, query}
                                       → emits context_window with the structured
                                          memory context for the side pane

Events the server emits:
  - connected, turn_started, tool_started, tool_finished, turn_finished,
    context_window
"""

from __future__ import annotations

import uuid
from typing import Any

from flask import request as flask_request

from agent.harness import agent_turn
from api.context import get_context_window
from api.identities import get_identity


_state: dict[str, Any] = {}


def init_events(*, agent_conn, memory_client, llm_client, socketio):
    _state.update(
        agent_conn=agent_conn,
        memory_client=memory_client,
        llm_client=llm_client,
        socketio=socketio,
    )


def register_events(socketio):
    @socketio.on("connect")
    def on_connect():
        sid = flask_request.sid
        socketio.emit("connected", {"sid": sid}, room=sid)

    @socketio.on("disconnect")
    def on_disconnect():
        pass  # OAMP holds state; nothing to clean up

    @socketio.on("new_thread")
    def on_new_thread():
        sid = flask_request.sid
        thread_id = uuid.uuid4().hex[:12]
        socketio.emit("thread_created", {"thread_id": thread_id}, room=sid)

    @socketio.on("send_message")
    def on_send_message(data):
        sid = flask_request.sid
        thread_id = data.get("thread_id") or uuid.uuid4().hex[:12]
        content = (data.get("content") or "").strip()
        identity = get_identity(data.get("as_user"))
        if not content:
            socketio.emit("error", {"message": "empty content"}, room=sid)
            socketio.emit("turn_finished", {
                "thread_id": thread_id, "answer": "(empty message ignored)",
                "trace": [], "elapsed_seconds": 0,
            }, room=sid)
            return

        # Outer try → no matter what blows up inside agent_turn / context build,
        # we ALWAYS emit a turn_finished event so the front-end stops showing
        # "agent is thinking…" indefinitely.
        import time as _t
        import traceback as _tb
        started = _t.time()
        try:
            result = agent_turn(
                user_query=content,
                thread_id=thread_id,
                agent_conn=_state["agent_conn"],
                memory_client=_state["memory_client"],
                llm_client=_state["llm_client"],
                socketio=socketio,
                sid=sid,
                identity=identity,
            )
        except Exception as e:
            _tb.print_exc()
            socketio.emit("turn_finished", {
                "thread_id": thread_id,
                "answer": f"⚠️ The agent crashed mid-turn: `{type(e).__name__}: {e}`. "
                          f"Backend logs have the full traceback. The thread itself "
                          f"is fine — try resending your message or starting a new thread.",
                "trace": [],
                "elapsed_seconds": round(_t.time() - started, 2),
            }, room=sid)
            return

        # Refresh the right-pane context window. Failure here mustn't block
        # the chat reply.
        try:
            payload = get_context_window(
                agent_conn=_state["agent_conn"],
                memory_client=_state["memory_client"],
                thread_id=thread_id,
                query=content,
            )
            socketio.emit("context_window", payload, room=sid)
        except Exception as e:
            _tb.print_exc()
            socketio.emit("error", {"message": f"context refresh failed: {e}"}, room=sid)

    @socketio.on("request_context_window")
    def on_request_context_window(data):
        sid = flask_request.sid
        payload = get_context_window(
            agent_conn=_state["agent_conn"],
            memory_client=_state["memory_client"],
            thread_id=data.get("thread_id", ""),
            query=data.get("query", ""),
        )
        socketio.emit("context_window", payload, room=sid)
