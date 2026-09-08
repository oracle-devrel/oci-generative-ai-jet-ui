"""
Live Log Dashboard for Agentic RAG Backend.

Provides:
- SSE endpoint at /logs/stream for real-time log streaming
- HTML dashboard at / for live log visualization
- Captures Python logging + stdout/stderr into a shared buffer
- DB category for Oracle database insert/query events
"""

import asyncio
import logging
import sys
import time
import json
import re
import threading
from datetime import datetime
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, StreamingResponse, Response

router = APIRouter(tags=["Live Logs"])
MAX_BUFFER = 500
_log_buffer = []
_subscribers = []
_buffer_idx = 0


def _emit(entry):
    """Push a log entry to buffer."""
    _log_buffer.append(entry)
    if len(_log_buffer) > MAX_BUFFER:
        _log_buffer.pop(0)


def _clean_message(text):
    """Strip markdown formatting and clean up log messages for display."""
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"\1", text)
    text = re.sub(r"_(.+?)_", r"\1", text)
    text = re.sub(r"`(.+?)`", r"\1", text)
    text = re.sub(r"  +", " ", text)
    return text.strip()


def _classify(text):
    """Classify a log line into a category for color-coding."""
    t = text.lower()
    has_check = "\u2705" in text
    has_warn_emoji = "\u26a0" in text
    if (
        any(k in t for k in ("error", "traceback", "exception", "failed"))
        and not has_check
    ):
        return "error"
    if any(k in t for k in ("warning", "warn")) or has_warn_emoji:
        return "warning"
    if any(
        k in t
        for k in (
            "insert into",
            "cursor.execute",
            ".commit",
            "oracle db",
            "oradb",
            "vector_store",
            "eventlogger",
            "event_log",
            "db connection",
            "create table",
            "drop table",
            "[eventlogger]",
            "a2a_events",
            "api_events",
            "model_events",
            "document_events",
            "query_events",
            "reasoning_events",
            "add_pdf_chunks",
            "add_web_chunks",
            "add_repo_chunks",
            "add_general_knowledge",
            "db event",
            "logged to db",
            "saved to oracle",
            "oracle ai database",
        )
    ):
        return "db"
    if any(
        k in t
        for k in (
            "planner",
            "researcher",
            "reasoner",
            "synthesizer",
            "[cotagent]",
            "[totagent]",
            "[reactagent]",
            "[selfreflectionagent]",
            "[leasttomostagent]",
            "[recursiveagent]",
            "[standardagent]",
            "[consistencyagent]",
            "[decomposedagent]",
            "chain-of-thought",
            "tree of thought",
            "self-reflection",
            "least-to-most",
            "decomposed",
            "react:",
            "consistency:",
            "recursive:",
            "standard:",
            "starting ensemble",
            "ensemble complete",
            "launching strategies",
            "processing query",
            "reasoning agent",
        )
    ):
        return "agent"
    if any(
        k in t
        for k in (
            "a2a",
            "agent.query",
            "agent.card",
            "agent.discover",
            "document.query",
            "task.",
            "reasoning.",
        )
    ):
        return "a2a"
    if any(k in t for k in ("ollama", "model", "gemma", "qwen", "llm")):
        return "model"
    if has_check or any(
        k in t
        for k in ("successfully", "initialized", "ready", "enabled", "already exists")
    ):
        return "success"
    if any(
        k in t
        for k in (
            "/v1/",
            "/a2a",
            "/query",
            "/upload",
            "http request",
            "http/1",
            "running on",
            "httpx:",
            "running on local url",
            "running on public url",
        )
    ):
        return "http"
    return "info"


_stream_lock = threading.Lock()
_stream_state = {}
_STREAM_FLUSH_MS = 300
_STREAM_IDLE_MS = 800
_STREAM_COUNTER = 0


def _next_stream_id():
    global _STREAM_COUNTER
    _STREAM_COUNTER += 1
    return f"s{_STREAM_COUNTER}"


def _flush_stream(stream_key):
    """Flush buffered stream text as a stream_update entry."""
    with _stream_lock:
        state = _stream_state.get(stream_key)
        if not state or not state["buffer"]:
            return
        text = state["buffer"]
        state["buffer"] = ""
        state["last_emit"] = time.monotonic()
    _emit(
        {
            "ts": datetime.now().strftime("%H:%M:%S.%f")[:-3],
            "level": "INFO",
            "cat": "model",
            "msg": text,
            "sid": state["sid"],
            "stype": "update",
        }
    )


def _end_stream(stream_key):
    """Finalize a stream after idle timeout."""
    with _stream_lock:
        state = _stream_state.pop(stream_key, None)
        if not state:
            return
        text = state["buffer"]
    _emit(
        {
            "ts": datetime.now().strftime("%H:%M:%S.%f")[:-3],
            "level": "INFO",
            "cat": _classify(text) if text else "model",
            "msg": text,
            "sid": state["sid"],
            "stype": "end",
        }
    )


def _is_streaming_fragment(text):
    """Detect if text looks like a streaming LLM token (very short, unstructured).

    Only matches actual token fragments from streaming LLM output.
    Normal log messages (even short ones) are NOT streaming fragments.
    """
    stripped = text.strip()
    if not stripped:
        return False
    if len(stripped) > 40:
        return False
    if "\n" in stripped:
        return False
    if re.match(
        r"^([\[({*#>]|[A-Z][a-zA-Z]+[\s:.]|[a-z]+[._][a-z]|https?://|/|[0-9]{2,}|[\u2705\u26A0\U0001F680\U0001F50D\U0001F4CB\U0001F4AC\U0001F3AF\U0001F4DD\U0001F914])",
        stripped,
    ):
        return False
    if re.match(r"^[A-Z][a-z]", stripped):
        return False
    return True


class LiveLogHandler(logging.Handler):
    def emit(self, record):
        try:
            msg = self.format(record)
            clean = _clean_message(msg)
            if not clean:
                return
            _emit(
                {
                    "ts": datetime.now().strftime("%H:%M:%S.%f")[:-3],
                    "level": record.levelname,
                    "cat": _classify(clean),
                    "msg": clean,
                }
            )
        except Exception:
            self.handleError(record)


class _TeeWriter:
    """Writes to original stream AND captures for SSE.

    Line-buffers output so each complete line becomes one log entry.
    Detects LLM streaming tokens (very short fragments without newlines)
    and consolidates them into a single updating dashboard line.
    """

    def __init__(self, original, stream_name="stdout"):
        self._original = original
        self._stream_name = stream_name
        self._line_buf = ""
        self._flush_timer = None
        self._lock = threading.Lock()

    def write(self, text):
        self._original.write(text)
        if not text:
            return None
        with self._lock:
            self._line_buf += text
            while "\n" in self._line_buf:
                line, self._line_buf = self._line_buf.split("\n", 1)
                line = line.strip()
                if line:
                    if _is_streaming_fragment(line):
                        self._emit_streaming(line)
                    else:
                        self._emit_line(line)
            # If there's remaining text without a newline, check if it's streaming
            if self._line_buf:
                if _is_streaming_fragment(self._line_buf):
                    fragment = self._line_buf
                    self._line_buf = ""
                    self._emit_streaming(fragment)
                else:
                    self._schedule_flush()

    def _schedule_flush(self):
        """Flush the line buffer after a short delay if no newline arrives."""
        if self._flush_timer is not None:
            self._flush_timer.cancel()

        def do_flush():
            with self._lock:
                buf = self._line_buf.strip()
                self._line_buf = ""
                self._flush_timer = None
            if buf:
                self._emit_line(buf)

        self._flush_timer = threading.Timer(0.5, do_flush)
        self._flush_timer.daemon = True
        self._flush_timer.start()

    def _emit_line(self, text):
        """Emit a complete line as a normal log entry."""
        clean = re.sub(r"\x1B\[[0-9;]*[mK]", "", text)
        clean = _clean_message(clean)
        if not clean:
            return None
        _emit(
            {
                "ts": datetime.now().strftime("%H:%M:%S.%f")[:-3],
                "level": "INFO" if self._stream_name == "stdout" else "ERROR",
                "cat": _classify(clean),
                "msg": clean,
            }
        )

    def _emit_streaming(self, text):
        """Route streaming text through the consolidation buffer."""
        stream_key = self._stream_name
        now = time.monotonic()
        with _stream_lock:
            state = _stream_state.get(stream_key)
            if state is None:
                sid = _next_stream_id()
                state = {
                    "sid": sid,
                    "buffer": text,
                    "last_emit": now,
                    "idle_timer": None,
                }
                _stream_state[stream_key] = state
            else:
                state["buffer"] += text
                if state["idle_timer"] is not None:
                    state["idle_timer"].cancel()
            # Schedule idle timeout to finalize the stream
            timer = threading.Timer(
                _STREAM_IDLE_MS / 1000.0, _end_stream, args=(stream_key,)
            )
            timer.daemon = True
            timer.start()
            state["idle_timer"] = timer
            # Flush if enough time has passed since last emit
            if (now - state["last_emit"]) * 1000 >= _STREAM_FLUSH_MS:
                pass  # will flush below
            else:
                return
        _flush_stream(stream_key)

    def flush(self):
        self._original.flush()

    def __getattr__(self, name):
        return getattr(self._original, name)


def install_log_capture():
    """Install log capture on Python logging + stdout/stderr."""
    handler = LiveLogHandler()
    handler.setFormatter(logging.Formatter("%(name)s: %(message)s"))
    logging.root.addHandler(handler)
    logging.root.setLevel(logging.INFO)
    sys.stdout = _TeeWriter(sys.__stdout__, "stdout")
    sys.stderr = _TeeWriter(sys.__stderr__, "stderr")


async def _event_generator(request):
    """Generate SSE events from log buffer."""
    _subscribers.append(True)
    last_idx = len(_log_buffer)
    try:
        # Send existing buffer first
        for entry in list(_log_buffer):
            yield f"data: {json.dumps(entry)}\n\n"
        # Stream new entries by polling buffer
        while True:
            if await request.is_disconnected():
                break
            await asyncio.sleep(0.5)
            # Check for new entries
            current_len = len(_log_buffer)
            if current_len > last_idx:
                # Send new entries
                for i in range(last_idx, current_len):
                    yield f"data: {json.dumps(_log_buffer[i])}\n\n"
                last_idx = current_len
            else:
                yield ": keepalive\n\n"
    finally:
        _subscribers.remove(True)


@router.get("/logs/stream")
async def log_stream(request: Request):
    """SSE endpoint for live log streaming."""
    return StreamingResponse(
        _event_generator(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/logs/history")
async def log_history(limit: int = 100):
    """Get recent log entries as JSON."""
    entries = list(_log_buffer)[-limit:]
    return {"count": len(entries), "entries": entries}


_FAVICON_SVG = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">\n<rect width="32" height="32" rx="6" fill="#0a0e17"/>\n<path d="M6 16c0-5.5 4.5-10 10-10s10 4.5 10 10-4.5 10-10 10S6 21.5 6 16zm3 0c0 3.9 3.1 7 7 7s7-3.1 7-7-3.1-7-7-7-7 3.1-7 7z" fill="#e85d26"/>\n<circle cx="16" cy="16" r="3" fill="#58a6ff"/>\n</svg>'


@router.get("/favicon.ico")
async def favicon():
    """Serve an inline SVG favicon."""
    return Response(
        content=_FAVICON_SVG,
        media_type="image/svg+xml",
        headers={"Cache-Control": "public, max-age=86400"},
    )


DASHBOARD_HTML = "<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n<title>Oracle Agentic RAG | Live System Monitor</title>\n<link rel=\"icon\" type=\"image/svg+xml\" href=\"/favicon.ico\">\n<link rel=\"preconnect\" href=\"https://fonts.googleapis.com\">\n<link rel=\"preconnect\" href=\"https://fonts.gstatic.com\" crossorigin>\n<link href=\"https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=DM+Sans:wght@400;500;600;700&display=swap\" rel=\"stylesheet\">\n<style>\n  :root {\n    --bg-deep: #050810;\n    --bg-main: #0a0e17;\n    --bg-surface: #0f1420;\n    --bg-elevated: #151b28;\n    --bg-hover: #1a2235;\n    --border: #1e2940;\n    --border-active: #2a3a5c;\n    --fg: #d0d8e8;\n    --fg-dim: #6b7a99;\n    --fg-muted: #4a5876;\n\n    /* Category palette - vivid, saturated */\n    --c-error: #ff4d6a;\n    --c-error-bg: #2a0a14;\n    --c-warning: #ffb347;\n    --c-warning-bg: #2a1c0a;\n    --c-a2a: #4dabf7;\n    --c-a2a-bg: #0a1a2e;\n    --c-agent: #b197fc;\n    --c-agent-bg: #1a0f2e;\n    --c-model: #ffd43b;\n    --c-model-bg: #2a250a;\n    --c-success: #51cf66;\n    --c-success-bg: #0a2a12;\n    --c-http: #38d9a9;\n    --c-http-bg: #0a2a22;\n    --c-db: #e85d26;\n    --c-db-bg: #2a120a;\n    --c-info: #6b7a99;\n    --c-info-bg: transparent;\n\n    /* Oracle accent */\n    --oracle-red: #e85d26;\n    --oracle-glow: rgba(232, 93, 38, 0.15);\n  }\n\n  * { margin: 0; padding: 0; box-sizing: border-box; }\n\n  body {\n    background: var(--bg-deep);\n    color: var(--fg);\n    font-family: 'DM Sans', -apple-system, BlinkMacSystemFont, sans-serif;\n    font-size: 14px;\n    line-height: 1.6;\n    overflow: hidden;\n    height: 100vh;\n  }\n\n  /* === HEADER === */\n  .header {\n    position: relative;\n    z-index: 20;\n    background: var(--bg-main);\n    border-bottom: 1px solid var(--border);\n    padding: 0 24px;\n    height: 56px;\n    display: flex;\n    align-items: center;\n    gap: 20px;\n  }\n\n  .header::after {\n    content: '';\n    position: absolute;\n    bottom: -1px;\n    left: 0;\n    right: 0;\n    height: 1px;\n    background: linear-gradient(90deg, transparent, var(--oracle-red), var(--c-a2a), transparent);\n    opacity: 0.4;\n  }\n\n  .brand {\n    display: flex;\n    align-items: center;\n    gap: 12px;\n    flex-shrink: 0;\n  }\n\n  .brand-icon {\n    width: 32px;\n    height: 32px;\n    border-radius: 8px;\n    background: linear-gradient(135deg, var(--oracle-red), #c24a1e);\n    display: flex;\n    align-items: center;\n    justify-content: center;\n    font-size: 15px;\n    font-weight: 700;\n    color: white;\n    font-family: 'IBM Plex Mono', monospace;\n    box-shadow: 0 2px 8px rgba(232, 93, 38, 0.3);\n  }\n\n  .brand-text {\n    display: flex;\n    flex-direction: column;\n    line-height: 1.2;\n  }\n\n  .brand-title {\n    font-size: 14px;\n    font-weight: 700;\n    color: var(--fg);\n    letter-spacing: -0.02em;\n  }\n\n  .brand-sub {\n    font-size: 10px;\n    font-weight: 500;\n    color: var(--fg-dim);\n    text-transform: uppercase;\n    letter-spacing: 0.08em;\n  }\n\n  .conn-status {\n    display: flex;\n    align-items: center;\n    gap: 8px;\n    padding: 5px 12px;\n    border-radius: 20px;\n    background: var(--bg-surface);\n    border: 1px solid var(--border);\n    font-size: 12px;\n    font-weight: 500;\n    color: var(--fg-dim);\n    transition: all 0.3s;\n  }\n\n  .conn-status.live {\n    border-color: rgba(81, 207, 102, 0.3);\n    color: var(--c-success);\n  }\n\n  .conn-status.dead {\n    border-color: rgba(255, 77, 106, 0.3);\n    color: var(--c-error);\n  }\n\n  .conn-dot {\n    width: 7px;\n    height: 7px;\n    border-radius: 50%;\n    background: var(--fg-dim);\n    transition: background 0.3s;\n  }\n\n  .conn-status.live .conn-dot {\n    background: var(--c-success);\n    box-shadow: 0 0 6px rgba(81, 207, 102, 0.5);\n    animation: glow-pulse 2s ease-in-out infinite;\n  }\n\n  .conn-status.dead .conn-dot {\n    background: var(--c-error);\n  }\n\n  @keyframes glow-pulse {\n    0%, 100% { opacity: 1; box-shadow: 0 0 6px rgba(81, 207, 102, 0.5); }\n    50% { opacity: 0.5; box-shadow: 0 0 2px rgba(81, 207, 102, 0.2); }\n  }\n\n  .header-spacer { flex: 1; }\n\n  /* === CONTROLS === */\n  .controls {\n    display: flex;\n    align-items: center;\n    gap: 8px;\n  }\n\n  .search-box {\n    position: relative;\n  }\n\n  .search-box input {\n    background: var(--bg-surface);\n    border: 1px solid var(--border);\n    color: var(--fg);\n    padding: 6px 12px 6px 32px;\n    border-radius: 8px;\n    font-size: 13px;\n    width: 220px;\n    font-family: 'IBM Plex Mono', monospace;\n    transition: border-color 0.2s, box-shadow 0.2s;\n    outline: none;\n  }\n\n  .search-box input:focus {\n    border-color: var(--border-active);\n    box-shadow: 0 0 0 3px rgba(77, 171, 247, 0.1);\n  }\n\n  .search-box input::placeholder {\n    color: var(--fg-muted);\n  }\n\n  .search-box .search-icon {\n    position: absolute;\n    left: 10px;\n    top: 50%;\n    transform: translateY(-50%);\n    color: var(--fg-muted);\n    font-size: 13px;\n    pointer-events: none;\n  }\n\n  .ctrl-btn {\n    background: var(--bg-surface);\n    border: 1px solid var(--border);\n    color: var(--fg-dim);\n    padding: 6px 14px;\n    border-radius: 8px;\n    font-size: 12px;\n    font-weight: 500;\n    cursor: pointer;\n    transition: all 0.15s;\n    font-family: 'DM Sans', sans-serif;\n    white-space: nowrap;\n  }\n\n  .ctrl-btn:hover {\n    background: var(--bg-hover);\n    border-color: var(--border-active);\n    color: var(--fg);\n  }\n\n  .ctrl-btn.active {\n    background: rgba(77, 171, 247, 0.1);\n    border-color: rgba(77, 171, 247, 0.3);\n    color: var(--c-a2a);\n  }\n\n  .ctrl-btn.danger:hover {\n    background: rgba(255, 77, 106, 0.1);\n    border-color: rgba(255, 77, 106, 0.3);\n    color: var(--c-error);\n  }\n\n  .ctrl-toggle {\n    display: flex;\n    align-items: center;\n    gap: 6px;\n    font-size: 12px;\n    color: var(--fg-dim);\n    cursor: pointer;\n    user-select: none;\n  }\n\n  .ctrl-toggle input[type=\"checkbox\"] {\n    accent-color: var(--c-a2a);\n    cursor: pointer;\n  }\n\n  /* === STATS BAR === */\n  .stats-bar {\n    display: flex;\n    align-items: center;\n    gap: 6px;\n    padding: 8px 24px;\n    background: var(--bg-main);\n    border-bottom: 1px solid var(--border);\n    overflow-x: auto;\n    flex-shrink: 0;\n  }\n\n  .stat-chip {\n    display: flex;\n    align-items: center;\n    gap: 6px;\n    padding: 3px 10px;\n    border-radius: 6px;\n    font-size: 12px;\n    font-weight: 600;\n    font-family: 'IBM Plex Mono', monospace;\n    white-space: nowrap;\n    cursor: pointer;\n    transition: all 0.15s;\n    border: 1px solid transparent;\n  }\n\n  .stat-chip:hover {\n    transform: translateY(-1px);\n  }\n\n  .stat-chip .stat-dot {\n    width: 6px;\n    height: 6px;\n    border-radius: 50%;\n    flex-shrink: 0;\n  }\n\n  .stat-chip.total { color: var(--fg-dim); background: var(--bg-surface); }\n  .stat-chip.total .stat-dot { background: var(--fg-dim); }\n  .stat-chip.a2a { color: var(--c-a2a); background: var(--c-a2a-bg); }\n  .stat-chip.a2a .stat-dot { background: var(--c-a2a); }\n  .stat-chip.agent { color: var(--c-agent); background: var(--c-agent-bg); }\n  .stat-chip.agent .stat-dot { background: var(--c-agent); }\n  .stat-chip.model { color: var(--c-model); background: var(--c-model-bg); }\n  .stat-chip.model .stat-dot { background: var(--c-model); }\n  .stat-chip.db { color: var(--c-db); background: var(--c-db-bg); }\n  .stat-chip.db .stat-dot { background: var(--c-db); }\n  .stat-chip.http { color: var(--c-http); background: var(--c-http-bg); }\n  .stat-chip.http .stat-dot { background: var(--c-http); }\n  .stat-chip.success { color: var(--c-success); background: var(--c-success-bg); }\n  .stat-chip.success .stat-dot { background: var(--c-success); }\n  .stat-chip.error { color: var(--c-error); background: var(--c-error-bg); }\n  .stat-chip.error .stat-dot { background: var(--c-error); }\n\n  .stat-chip.filter-active {\n    border-color: currentColor;\n    box-shadow: 0 0 8px currentColor;\n  }\n\n  .stat-sep {\n    width: 1px;\n    height: 20px;\n    background: var(--border);\n    margin: 0 4px;\n    flex-shrink: 0;\n  }\n\n  /* === LOG CONTAINER === */\n  #log-container {\n    flex: 1;\n    overflow-y: auto;\n    overflow-x: hidden;\n    scroll-behavior: smooth;\n    display: flex;\n    flex-direction: column-reverse;\n  }\n\n  .log-wrap {\n    display: flex;\n    flex-direction: column;\n    height: calc(100vh - 56px - 40px);\n  }\n\n  /* === LOG LINES === */\n  .log-line {\n    display: flex;\n    align-items: flex-start;\n    gap: 0;\n    padding: 2px 24px;\n    border-left: 3px solid transparent;\n    font-family: 'IBM Plex Mono', monospace;\n    font-size: 12.5px;\n    line-height: 1.65;\n    transition: background 0.1s;\n    animation: line-in 0.2s ease-out;\n  }\n\n  @keyframes line-in {\n    from { opacity: 0; transform: translateY(4px); }\n    to { opacity: 1; transform: translateY(0); }\n  }\n\n  .log-line:hover {\n    background: var(--bg-hover);\n  }\n\n  /* Category border + background */\n  .log-line.error   { border-left-color: var(--c-error);   background: var(--c-error-bg); }\n  .log-line.warning { border-left-color: var(--c-warning); }\n  .log-line.a2a     { border-left-color: var(--c-a2a); }\n  .log-line.agent   { border-left-color: var(--c-agent); }\n  .log-line.model   { border-left-color: var(--c-model); }\n  .log-line.success { border-left-color: var(--c-success); }\n  .log-line.http    { border-left-color: var(--c-http); }\n  .log-line.db      { border-left-color: var(--c-db); background: var(--c-db-bg); }\n  .log-line.info    { border-left-color: transparent; }\n\n  /* Streaming line: pulsing left border while active */\n  .log-line.streaming {\n    border-left-width: 3px;\n    border-left-style: solid;\n    animation: stream-pulse 1s ease-in-out infinite;\n  }\n  .log-line.streaming .log-cat::after {\n    content: ' ...';\n    animation: stream-dots 1.5s steps(3, end) infinite;\n  }\n  @keyframes stream-pulse {\n    0%, 100% { border-left-color: var(--c-model); }\n    50% { border-left-color: var(--c-a2a); }\n  }\n  @keyframes stream-dots {\n    0% { content: ''; }\n    33% { content: ' .'; }\n    66% { content: ' ..'; }\n    100% { content: ' ...'; }\n  }\n\n  .log-ts {\n    color: var(--fg-muted);\n    min-width: 90px;\n    flex-shrink: 0;\n    font-size: 11px;\n    padding-top: 1px;\n  }\n\n  .log-cat {\n    min-width: 64px;\n    flex-shrink: 0;\n    font-size: 10px;\n    font-weight: 600;\n    text-transform: uppercase;\n    letter-spacing: 0.06em;\n    padding-top: 2px;\n  }\n\n  .log-cat.error   { color: var(--c-error); }\n  .log-cat.warning { color: var(--c-warning); }\n  .log-cat.a2a     { color: var(--c-a2a); }\n  .log-cat.agent   { color: var(--c-agent); }\n  .log-cat.model   { color: var(--c-model); }\n  .log-cat.success { color: var(--c-success); }\n  .log-cat.http    { color: var(--c-http); }\n  .log-cat.db      { color: var(--c-db); }\n  .log-cat.info    { color: var(--fg-muted); }\n\n  .log-msg {\n    flex: 1;\n    color: var(--fg);\n    white-space: pre-wrap;\n    word-break: break-word;\n    min-width: 0;\n  }\n\n  .log-msg .hl {\n    background: rgba(255, 212, 59, 0.15);\n    color: var(--c-model);\n    padding: 0 3px;\n    border-radius: 3px;\n    font-weight: 500;\n  }\n\n  .log-msg .hl-db {\n    background: rgba(232, 93, 38, 0.15);\n    color: var(--c-db);\n    padding: 0 3px;\n    border-radius: 3px;\n    font-weight: 500;\n  }\n\n  /* === EMPTY STATE === */\n  .empty-state {\n    display: flex;\n    flex-direction: column;\n    align-items: center;\n    justify-content: center;\n    padding: 80px 20px;\n    color: var(--fg-dim);\n    text-align: center;\n    animation: fade-in 0.6s ease-out;\n  }\n\n  @keyframes fade-in {\n    from { opacity: 0; transform: translateY(12px); }\n    to { opacity: 1; transform: translateY(0); }\n  }\n\n  .empty-icon {\n    width: 64px;\n    height: 64px;\n    border-radius: 16px;\n    background: var(--bg-elevated);\n    border: 1px solid var(--border);\n    display: flex;\n    align-items: center;\n    justify-content: center;\n    margin-bottom: 16px;\n  }\n\n  .empty-icon svg {\n    width: 28px;\n    height: 28px;\n    opacity: 0.5;\n  }\n\n  .empty-title {\n    font-size: 15px;\n    font-weight: 600;\n    margin-bottom: 6px;\n    color: var(--fg);\n  }\n\n  .empty-desc {\n    font-size: 12px;\n    color: var(--fg-muted);\n    max-width: 320px;\n  }\n\n  /* === SCROLLBAR === */\n  #log-container::-webkit-scrollbar {\n    width: 8px;\n  }\n  #log-container::-webkit-scrollbar-track {\n    background: transparent;\n  }\n  #log-container::-webkit-scrollbar-thumb {\n    background: var(--border);\n    border-radius: 4px;\n  }\n  #log-container::-webkit-scrollbar-thumb:hover {\n    background: var(--border-active);\n  }\n\n  /* === RESPONSIVE === */\n  @media (max-width: 768px) {\n    .header { padding: 0 12px; gap: 10px; }\n    .brand-text { display: none; }\n    .search-box input { width: 140px; }\n    .log-line { padding: 2px 12px; font-size: 11px; }\n    .log-ts { min-width: 70px; }\n    .stats-bar { padding: 6px 12px; }\n  }\n</style>\n</head>\n<body>\n\n<div class=\"header\">\n  <div class=\"brand\">\n    <div class=\"brand-icon\">O</div>\n    <div class=\"brand-text\">\n      <div class=\"brand-title\">Agentic RAG</div>\n      <div class=\"brand-sub\">Live System Monitor</div>\n    </div>\n  </div>\n\n  <div class=\"conn-status\" id=\"conn-status\">\n    <div class=\"conn-dot\"></div>\n    <span id=\"conn-text\">Connecting</span>\n  </div>\n\n  <div class=\"header-spacer\"></div>\n\n  <div class=\"controls\">\n    <div class=\"search-box\">\n      <span class=\"search-icon\">&#x2315;</span>\n      <input type=\"text\" id=\"filter\" placeholder=\"Filter logs...\" oninput=\"applyFilter()\" spellcheck=\"false\">\n    </div>\n    <label class=\"ctrl-toggle\">\n      <input type=\"checkbox\" id=\"autoscroll\" checked>\n      <span>Auto-scroll</span>\n    </label>\n    <button class=\"ctrl-btn\" onclick=\"clearLogs()\" title=\"Clear all logs\">Clear</button>\n    <button class=\"ctrl-btn\" id=\"pause-btn\" onclick=\"togglePause()\" title=\"Pause/resume stream\">Pause</button>\n  </div>\n</div>\n\n<div class=\"log-wrap\">\n  <div class=\"stats-bar\" id=\"stats-bar\"></div>\n  <div id=\"log-container\">\n    <div class=\"empty-state\" id=\"empty\">\n      <div class=\"empty-icon\">\n        <svg viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.5\" stroke-linecap=\"round\" stroke-linejoin=\"round\">\n          <path d=\"M12 2L2 7l10 5 10-5-10-5z\"/>\n          <path d=\"M2 17l10 5 10-5\"/>\n          <path d=\"M2 12l10 5 10-5\"/>\n        </svg>\n      </div>\n      <div class=\"empty-title\">Awaiting Backend Activity</div>\n      <div class=\"empty-desc\">\n        Send requests to the API, use the Gradio UI, or trigger A2A protocol calls to see real-time logs here.\n      </div>\n    </div>\n  </div>\n</div>\n\n<script>\nconst container = document.getElementById('log-container');\nconst empty = document.getElementById('empty');\nconst connStatus = document.getElementById('conn-status');\nconst connText = document.getElementById('conn-text');\nconst filterInput = document.getElementById('filter');\nconst statsBar = document.getElementById('stats-bar');\nlet paused = false;\nlet lineCount = 0;\nlet catFilter = null;  // null = show all, string = filter by category\nconst counts = { total: 0, a2a: 0, agent: 0, model: 0, db: 0, http: 0, success: 0, error: 0 };\n\nfunction setConnected(connected) {\n  connStatus.className = 'conn-status ' + (connected ? 'live' : 'dead');\n  connText.textContent = connected ? 'Live' : 'Reconnecting';\n}\n\nfunction escapeHtml(s) {\n  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');\n}\n\nfunction updateStats() {\n  const chips = [\n    { cat: 'total', label: 'Total', count: counts.total },\n    null, // separator\n    { cat: 'a2a', label: 'A2A', count: counts.a2a },\n    { cat: 'agent', label: 'Agent', count: counts.agent },\n    { cat: 'model', label: 'Model', count: counts.model },\n    { cat: 'db', label: 'DB', count: counts.db },\n    { cat: 'http', label: 'HTTP', count: counts.http },\n    { cat: 'success', label: 'OK', count: counts.success },\n    { cat: 'error', label: 'Errors', count: counts.error },\n  ];\n\n  statsBar.innerHTML = chips.map(c => {\n    if (!c) return '<div class=\"stat-sep\"></div>';\n    const active = catFilter === c.cat ? ' filter-active' : '';\n    return '<div class=\"stat-chip ' + c.cat + active + '\" onclick=\"toggleCatFilter(\\'' + c.cat + '\\')\">' +\n      '<div class=\"stat-dot\"></div>' +\n      '<span>' + c.label + ' ' + c.count + '</span>' +\n    '</div>';\n  }).join('');\n}\n\nfunction toggleCatFilter(cat) {\n  if (cat === 'total' || catFilter === cat) {\n    catFilter = null;\n  } else {\n    catFilter = cat;\n  }\n  applyFilter();\n  updateStats();\n}\n\n// --- Streaming consolidation ---\nconst activeStreams = {};  // sid -> { el, fullText }\n\nfunction highlightMsg(text) {\n  let h = escapeHtml(text);\n  // Highlight agent IDs\n  h = h.replace(/(planner|researcher|reasoner|synthesizer)_agent_v\\d/gi,\n    '<span class=\"hl\">$&</span>');\n  // Highlight A2A methods\n  h = h.replace(/(agent\\.query|document\\.query|health\\.check|task\\.\\w+|reasoning\\.\\w+)/gi,\n    '<span class=\"hl\">$&</span>');\n  // Highlight DB operations\n  h = h.replace(/(INSERT INTO|CREATE TABLE|DROP TABLE|COMMIT|cursor\\.execute|EventLogger|OraDB\\w+)/gi,\n    '<span class=\"hl-db\">$&</span>');\n  return h;\n}\n\nfunction addLine(entry) {\n  if (paused) return;\n\n  // --- Handle streaming entries (have sid field) ---\n  if (entry.sid) {\n    if (entry.stype === 'end') {\n      // Finalize the stream line\n      const stream = activeStreams[entry.sid];\n      if (stream && stream.el) {\n        stream.el.classList.remove('streaming');\n        // Re-classify final text\n        const finalCat = entry.cat || 'info';\n        stream.el.dataset.msg = stream.fullText.toLowerCase();\n      }\n      delete activeStreams[entry.sid];\n      return;\n    }\n\n    // stype === 'update': append text to existing stream line\n    let stream = activeStreams[entry.sid];\n    if (!stream) {\n      // First chunk of this stream - create line\n      counts.total++;\n      if (counts[entry.cat] !== undefined) counts[entry.cat]++;\n      updateStats();\n\n      if (empty.style.display !== 'none') empty.style.display = 'none';\n\n      const div = document.createElement('div');\n      div.className = 'log-line model streaming';\n      div.dataset.sid = entry.sid;\n      div.dataset.cat = entry.cat || 'model';\n      div.dataset.msg = '';\n\n      div.innerHTML =\n        '<span class=\"log-ts\">' + entry.ts + '</span>' +\n        '<span class=\"log-cat model\">stream</span>' +\n        '<span class=\"log-msg\"></span>';\n\n      container.appendChild(div);\n      lineCount++;\n\n      stream = { el: div, fullText: '' };\n      activeStreams[entry.sid] = stream;\n    }\n\n    // Append new text\n    stream.fullText += entry.msg;\n    stream.el.dataset.msg = stream.fullText.toLowerCase();\n    // Update the message span with accumulated text\n    const msgSpan = stream.el.querySelector('.log-msg');\n    if (msgSpan) {\n      msgSpan.innerHTML = highlightMsg(stream.fullText);\n    }\n    // Update timestamp to latest\n    const tsSpan = stream.el.querySelector('.log-ts');\n    if (tsSpan) tsSpan.textContent = entry.ts;\n\n    // Apply current filters\n    const f = filterInput.value.toLowerCase();\n    const textMatch = !f || stream.fullText.toLowerCase().includes(f) || (entry.cat || '').includes(f);\n    const catMatch = !catFilter || (entry.cat || 'model') === catFilter;\n    stream.el.style.display = (textMatch && catMatch) ? '' : 'none';\n\n    if (document.getElementById('autoscroll').checked) {\n      container.scrollTop = 0;\n    }\n    return;\n  }\n\n  // --- Normal (non-streaming) entry ---\n  counts.total++;\n  if (counts[entry.cat] !== undefined) counts[entry.cat]++;\n  updateStats();\n\n  if (empty.style.display !== 'none') empty.style.display = 'none';\n\n  const div = document.createElement('div');\n  div.className = 'log-line ' + entry.cat;\n  div.dataset.msg = entry.msg.toLowerCase();\n  div.dataset.cat = entry.cat;\n\n  div.innerHTML =\n    '<span class=\"log-ts\">' + entry.ts + '</span>' +\n    '<span class=\"log-cat ' + entry.cat + '\">' + entry.cat + '</span>' +\n    '<span class=\"log-msg\">' + highlightMsg(entry.msg) + '</span>';\n\n  // Apply current filters\n  const f = filterInput.value.toLowerCase();\n  const textMatch = !f || entry.msg.toLowerCase().includes(f) || entry.cat.includes(f);\n  const catMatch = !catFilter || entry.cat === catFilter;\n  if (!textMatch || !catMatch) {\n    div.style.display = 'none';\n  }\n\n  container.appendChild(div);\n  lineCount++;\n\n  // Trim old lines (keep max 2000)\n  while (lineCount > 2000) {\n    const first = container.querySelector('.log-line');\n    if (first) { container.removeChild(first); lineCount--; }\n    else break;\n  }\n\n  if (document.getElementById('autoscroll').checked) {\n    container.scrollTop = 0;\n  }\n}\n\nfunction applyFilter() {\n  const f = filterInput.value.toLowerCase();\n  container.querySelectorAll('.log-line').forEach(el => {\n    const textMatch = !f || el.dataset.msg.includes(f) || el.className.includes(f);\n    const catMatch = !catFilter || el.dataset.cat === catFilter;\n    el.style.display = (textMatch && catMatch) ? '' : 'none';\n  });\n}\n\nfunction clearLogs() {\n  container.querySelectorAll('.log-line').forEach(el => el.remove());\n  lineCount = 0;\n  Object.keys(counts).forEach(k => counts[k] = 0);\n  updateStats();\n  empty.style.display = '';\n}\n\nfunction togglePause() {\n  paused = !paused;\n  const btn = document.getElementById('pause-btn');\n  btn.textContent = paused ? 'Resume' : 'Pause';\n  btn.className = 'ctrl-btn' + (paused ? ' active' : '');\n  if (paused) {\n    connText.textContent = 'Paused';\n  } else {\n    connText.textContent = 'Live';\n  }\n}\n\nfunction connect() {\n  const es = new EventSource('/logs/stream');\n\n  es.onopen = () => {\n    setConnected(true);\n    if (!paused) connText.textContent = 'Live';\n  };\n\n  es.onmessage = (e) => {\n    try { addLine(JSON.parse(e.data)); } catch(err) {}\n  };\n\n  es.onerror = () => {\n    setConnected(false);\n    es.close();\n    setTimeout(connect, 3000);\n  };\n}\n\n// Keyboard shortcuts\ndocument.addEventListener('keydown', (e) => {\n  // Ctrl/Cmd + K = focus filter\n  if ((e.ctrlKey || e.metaKey) && e.key === 'k') {\n    e.preventDefault();\n    filterInput.focus();\n    filterInput.select();\n  }\n  // Escape = clear filter\n  if (e.key === 'Escape') {\n    filterInput.value = '';\n    catFilter = null;\n    applyFilter();\n    updateStats();\n    filterInput.blur();\n  }\n  // Space = toggle pause (when not in input)\n  if (e.key === ' ' && document.activeElement !== filterInput) {\n    e.preventDefault();\n    togglePause();\n  }\n});\n\nupdateStats();\nconnect();\n</script>\n</body>\n</html>"


@router.get("/", response_class=HTMLResponse)
async def live_dashboard():
    """Serve the live log dashboard."""
    return DASHBOARD_HTML
