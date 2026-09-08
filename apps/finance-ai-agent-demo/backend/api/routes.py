"""REST API routes."""

import logging
import os
import uuid

from flask import Blueprint, jsonify, request
from werkzeug.utils import secure_filename

logger = logging.getLogger(__name__)

api_bp = Blueprint("api", __name__)

# These get set by app.py during init
_app_state = {}


def init_routes(
    conn,
    embedding_model,
    memory_manager,
    knowledge_base_vs,
    llm_client,
    query_logger,
    file_ingestor,
    socketio,
):
    _app_state.update(
        {
            "conn": conn,
            "embedding_model": embedding_model,
            "memory_manager": memory_manager,
            "knowledge_base_vs": knowledge_base_vs,
            "llm_client": llm_client,
            "query_logger": query_logger,
            "file_ingestor": file_ingestor,
            "socketio": socketio,
        }
    )


def _require_memory_manager():
    """Return the memory_manager or abort with 503 if unavailable."""
    mm = _app_state.get("memory_manager")
    if mm is None:
        return None
    return mm


@api_bp.route("/api/health", methods=["GET"])
def health():
    """Health check: tests DB connection + embedding model."""
    status = {"status": "ok", "database": "unknown", "embedding_model": "unknown"}
    try:
        conn = _app_state["conn"]
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM DUAL")
            cur.fetchone()
        status["database"] = "connected"
    except Exception as e:
        status["database"] = f"error: {e}"
        status["status"] = "degraded"

    try:
        emb = _app_state["embedding_model"]
        if emb:
            status["embedding_model"] = "loaded"
    except Exception as e:
        status["embedding_model"] = f"error: {e}"

    return jsonify(status)


@api_bp.route("/api/chat", methods=["POST"])
def chat():
    """Send a message and get a response (non-streaming fallback)."""
    from agent.harness import call_agent

    data = request.json or {}
    message = data.get("message", "")
    thread_id = data.get("thread_id", f"thread-{str(uuid.uuid4())[:8]}")

    if not message:
        return jsonify({"error": "No message provided"}), 400

    if _app_state.get("memory_manager") is None:
        return jsonify(
            {
                "error": "Database not available. Start Oracle Docker container and restart the server."
            }
        ), 503

    _app_state["query_logger"].clear()

    result = call_agent(
        query=message,
        thread_id=thread_id,
        conn=_app_state["conn"],
        embedding_model=_app_state["embedding_model"],
        memory_manager=_app_state["memory_manager"],
        llm_client=_app_state["llm_client"],
        query_logger=_app_state["query_logger"],
        socketio=_app_state["socketio"],
    )

    return jsonify(
        {
            "response": result["response"],
            "thread_id": result["thread_id"],
            "message_id": result["message_id"],
            "steps": result["steps"],
            "elapsed_s": result["elapsed_s"],
            "query_summary": _app_state["query_logger"].get_summary(),
        }
    )


@api_bp.route("/api/threads", methods=["GET"])
def list_threads():
    """List all conversation threads."""
    mm = _require_memory_manager()
    if mm is None:
        return jsonify(
            {
                "error": "Database not available. Start Oracle Docker container and restart the server."
            }
        ), 503
    threads = mm.get_threads()
    return jsonify(threads)


@api_bp.route("/api/threads", methods=["POST"])
def create_thread():
    """Create a new empty thread."""
    thread_id = f"thread-{str(uuid.uuid4())[:8]}"
    return jsonify({"thread_id": thread_id, "created_at": None})


@api_bp.route("/api/threads/<thread_id>/messages", methods=["GET"])
def get_thread_messages(thread_id):
    """Get full message history for a thread."""
    mm = _require_memory_manager()
    if mm is None:
        return jsonify(
            {
                "error": "Database not available. Start Oracle Docker container and restart the server."
            }
        ), 503
    messages = mm.read_conversational_memory_raw(thread_id)
    return jsonify(messages)


@api_bp.route("/api/threads/<thread_id>/messages", methods=["DELETE"])
def clear_thread_messages(thread_id):
    """Clear all messages for a thread."""
    confirm = request.headers.get("X-Confirm-Delete")
    if confirm != "true":
        return jsonify({"error": "Confirmation required. Set X-Confirm-Delete: true header."}), 400

    mm = _require_memory_manager()
    if mm is None:
        return jsonify(
            {
                "error": "Database not available. Start Oracle Docker container and restart the server."
            }
        ), 503
    count = mm.delete_thread_messages(thread_id)
    return jsonify({"thread_id": thread_id, "messages_deleted": count})


@api_bp.route("/api/threads/search/<thread_id_fragment>", methods=["GET"])
def search_threads(thread_id_fragment):
    """Search for a thread by partial ID match."""
    mm = _require_memory_manager()
    if mm is None:
        return jsonify(
            {
                "error": "Database not available. Start Oracle Docker container and restart the server."
            }
        ), 503
    threads = mm.get_threads(limit=100)
    matches = [t for t in threads if thread_id_fragment.lower() in t["thread_id"].lower()]
    return jsonify(matches)


@api_bp.route("/api/upload", methods=["POST"])
def upload_file():
    """Handle file upload, process, and ingest into knowledge base."""
    from ingestion.file_processor import FileProcessor

    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    thread_id = request.form.get("thread_id", "default")

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in FileProcessor.SUPPORTED_TYPES:
        return jsonify({"error": f"Unsupported file type: {ext}"}), 400

    upload_dir = os.path.join("uploads", thread_id)
    os.makedirs(upload_dir, exist_ok=True)
    filepath = os.path.join(upload_dir, secure_filename(file.filename))
    file.save(filepath)

    if _app_state.get("file_ingestor") is None:
        return jsonify(
            {"error": "Database not available. File ingestion requires Oracle DB connection."}
        ), 503

    result = _app_state["file_ingestor"].ingest(filepath=filepath, thread_id=thread_id)

    return jsonify(
        {
            "filename": result["filename"],
            "file_type": result["file_type"],
            "file_size_bytes": os.path.getsize(filepath),
            "chunks_created": result["chunks_created"],
            "storage_path": filepath,
            "status": result["status"],
        }
    )


@api_bp.route("/api/uploads/<thread_id>", methods=["GET"])
def list_uploads(thread_id):
    """List all uploaded files for a thread."""
    upload_dir = os.path.join("uploads", thread_id)
    if not os.path.exists(upload_dir):
        return jsonify([])

    files = []
    for f in os.listdir(upload_dir):
        fpath = os.path.join(upload_dir, f)
        files.append(
            {
                "filename": f,
                "file_type": os.path.splitext(f)[1].lower().lstrip("."),
                "file_size_bytes": os.path.getsize(fpath),
            }
        )
    return jsonify(files)


@api_bp.route("/api/context/<thread_id>/usage", methods=["GET"])
def context_usage(thread_id):
    """Get current context window usage breakdown."""
    from agent.context_engineering import calculate_context_usage, get_token_breakdown

    mm = _require_memory_manager()
    if mm is None:
        return jsonify(
            {
                "error": "Database not available. Start Oracle Docker container and restart the server."
            }
        ), 503
    try:
        context = mm.read_conversational_memory(thread_id)
    except Exception as e:
        logger.warning("Failed to read conversational memory for context usage: %s", e)
        context = ""

    usage = calculate_context_usage(context)
    breakdown = get_token_breakdown(mm, thread_id, "")

    return jsonify(
        {
            "total_tokens": usage["tokens"],
            "max_tokens": usage["max"],
            "percentage": usage["percent"],
            "breakdown": breakdown,
        }
    )


@api_bp.route("/api/context/<thread_id>/compact", methods=["POST"])
def compact_context(thread_id):
    """Trigger context compaction."""
    from agent.context_engineering import (
        calculate_context_usage,
        summarize_conversation_for_thread,
    )

    mm = _require_memory_manager()
    if mm is None:
        return jsonify(
            {
                "error": "Database not available. Start Oracle Docker container and restart the server."
            }
        ), 503

    try:
        before_ctx = mm.read_conversational_memory(thread_id)
    except Exception as e:
        logger.warning("Failed to read pre-compaction memory: %s", e)
        before_ctx = ""
    before_usage = calculate_context_usage(before_ctx)

    result = summarize_conversation_for_thread(thread_id, mm, _app_state["llm_client"])

    try:
        after_ctx = mm.read_conversational_memory(thread_id)
    except Exception as e:
        logger.warning("Failed to read post-compaction memory: %s", e)
        after_ctx = ""
    after_usage = calculate_context_usage(after_ctx)

    return jsonify(
        {
            "summary_id": result.get("id"),
            "description": result.get("description", ""),
            "messages_compacted": result.get("messages_compacted", 0),
            "tokens_before": before_usage["tokens"],
            "tokens_after": after_usage["tokens"],
        }
    )
