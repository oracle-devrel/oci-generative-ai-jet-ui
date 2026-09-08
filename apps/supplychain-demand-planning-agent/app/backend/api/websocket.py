"""WebSocket endpoint that streams supervisor events to the frontend."""

from __future__ import annotations

import json
import logging
import uuid

from app.backend.agent.streaming import translate_events
from app.backend.agent.supervisor import get_supervisor
from fastapi import WebSocket, WebSocketDisconnect

log = logging.getLogger("app.ws")


async def _run_supervisor(websocket: WebSocket, message: str, thread_id: str) -> None:
    """Invoke the supervisor with `astream_events`, push translated events out."""
    supervisor = await get_supervisor()

    raw = supervisor.astream_events(
        {"messages": [{"role": "user", "content": message}]},
        config={"configurable": {"thread_id": thread_id}},
        version="v2",
    )

    final_content = ""
    async for event in translate_events(raw):
        if event.get("type") == "token" and event.get("agent") == "supervisor":
            final_content += event.get("token", "")
        await websocket.send_text(json.dumps(event))

    # Emit a definitive final_answer with the accumulated supervisor text.
    await websocket.send_text(
        json.dumps(
            {
                "type": "final_answer",
                "content": final_content,
            }
        )
    )


async def chat_websocket(websocket: WebSocket) -> None:
    """One WebSocket = one ongoing conversation (one `thread_id`).

    Client message shape:
        {"type": "user_message", "content": "...", "thread_id": "optional"}

    Server pushes events of the shape defined in agent/streaming.py.
    """
    await websocket.accept()
    thread_id = f"ws-{uuid.uuid4().hex[:12]}"
    await websocket.send_text(json.dumps({"type": "session", "thread_id": thread_id}))

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_text(
                    json.dumps(
                        {
                            "type": "error",
                            "message": "invalid JSON payload",
                        }
                    )
                )
                continue

            if payload.get("type") == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
                continue

            if payload.get("type") != "user_message":
                await websocket.send_text(
                    json.dumps(
                        {
                            "type": "error",
                            "message": f"unsupported payload type: {payload.get('type')}",
                        }
                    )
                )
                continue

            user_thread_id = payload.get("thread_id") or thread_id
            message = (payload.get("content") or "").strip()
            if not message:
                continue

            # Echo the user message back so the chat UI can render it.
            await websocket.send_text(
                json.dumps(
                    {
                        "type": "user_message",
                        "content": message,
                        "thread_id": user_thread_id,
                    }
                )
            )

            try:
                await _run_supervisor(websocket, message, user_thread_id)
            except Exception as e:
                log.exception("supervisor run failed")
                await websocket.send_text(
                    json.dumps(
                        {
                            "type": "error",
                            "message": f"{type(e).__name__}: {e}",
                        }
                    )
                )

    except WebSocketDisconnect:
        log.info("websocket disconnected (thread=%s)", thread_id)
    except Exception:
        log.exception("websocket error")
        try:
            await websocket.close()
        except Exception:
            pass
