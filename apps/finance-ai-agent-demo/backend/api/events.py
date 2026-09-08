"""WebSocket event handlers."""

import json
import logging
import time
import uuid

from flask_socketio import emit

logger = logging.getLogger(__name__)

_app_state = {}


def init_events(
    conn,
    embedding_model,
    memory_manager,
    llm_client,
    query_logger,
    socketio,
    extra_connections=None,
    converged_conn=None,
    converged_memory_manager=None,
    sprawl_extra=None,
):
    _app_state.update(
        {
            "conn": conn,
            "embedding_model": embedding_model,
            "memory_manager": memory_manager,
            "llm_client": llm_client,
            "query_logger": query_logger,
            "socketio": socketio,
            "extra_connections": extra_connections or {},
            "converged_conn": converged_conn,
            "converged_memory_manager": converged_memory_manager,
            "sprawl_extra": sprawl_extra or {},
        }
    )


def register_events(socketio):
    """Register all WebSocket event handlers."""

    @socketio.on("connect")
    def handle_connect():
        comparison_ok = bool(_app_state.get("converged_conn") and _app_state.get("sprawl_extra"))
        emit("connected", {"status": "ok", "comparison_available": comparison_ok})

    @socketio.on("disconnect")
    def handle_disconnect():
        pass

    @socketio.on("send_message")
    def handle_message(data):
        """Handle incoming chat message, run agent, emit response + queries + tool calls."""
        from agent.context_engineering import calculate_context_usage, get_token_breakdown
        from agent.harness import call_agent

        message = data.get("message", "")
        thread_id = data.get("thread_id", f"thread-{str(uuid.uuid4())[:8]}")

        if not message:
            emit("error", {"message": "Empty message"})
            return

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
            extra_connections=_app_state.get("extra_connections"),
        )

        emit(
            "agent_complete",
            {
                "message_id": result["message_id"],
                "thread_id": result["thread_id"],
                "response": result["response"],
                "steps": result["steps"],
                "elapsed_s": result["elapsed_s"],
                "query_summary": _app_state["query_logger"].get_summary(),
            },
        )

        # Emit token usage update
        mm = _app_state["memory_manager"]
        try:
            ctx = mm.read_conversational_memory(thread_id)
        except Exception as e:
            logger.warning("Failed to read conversational memory for token usage: %s", e)
            ctx = ""
        usage = calculate_context_usage(ctx)
        breakdown = get_token_breakdown(mm, thread_id, message)

        emit(
            "token_usage_update",
            {
                "thread_id": thread_id,
                "total_tokens": usage["tokens"],
                "max_tokens": usage["max"],
                "percentage": usage["percent"],
                "breakdown": breakdown,
            },
        )

        # Auto-refresh context window so Context tab reflects the latest conversation
        handle_request_context_window({"thread_id": thread_id, "query": message})

    @socketio.on("trigger_compaction")
    def handle_compaction(data):
        """Handle auto-compaction request."""
        from agent.context_engineering import (
            calculate_context_usage,
            get_token_breakdown,
            summarize_conversation_for_thread,
        )

        thread_id = data.get("thread_id", "")
        mm = _app_state["memory_manager"]

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

        emit(
            "compaction_complete",
            {
                "summary_id": result.get("id"),
                "description": result.get("description", ""),
                "tokens_before": before_usage["tokens"],
                "tokens_after": after_usage["tokens"],
                "messages_compacted": result.get("messages_compacted", 0),
            },
        )

        breakdown = get_token_breakdown(mm, thread_id, "")
        emit(
            "token_usage_update",
            {
                "thread_id": thread_id,
                "total_tokens": after_usage["tokens"],
                "max_tokens": after_usage["max"],
                "percentage": after_usage["percent"],
                "breakdown": breakdown,
            },
        )

        # Auto-refresh context window so Context tab reflects post-compaction state
        handle_request_context_window({"thread_id": thread_id, "query": ""})

    @socketio.on("load_thread")
    def handle_load_thread(data):
        """Load a conversation thread by ID, including tool call history."""
        thread_id = data.get("thread_id", "")
        mm = _app_state["memory_manager"]
        messages = mm.read_conversational_memory_raw(thread_id)

        if not messages:
            emit(
                "thread_loaded",
                {
                    "thread_id": thread_id,
                    "messages": [],
                    "error": "Thread not found",
                },
            )
            return

        # Load tool logs for this thread and attach to assistant messages.
        # Both lists are ordered chronologically (ASC). Tool logs executed
        # BEFORE an assistant message belong to that message. We consume
        # tool_logs from the front so each log is matched at most once.
        tool_logs = mm.get_tool_logs_for_thread(thread_id)
        log_idx = 0

        for msg in messages:
            msg["toolCalls"] = []
            if msg["role"] == "assistant":
                msg_ts = msg["timestamp"]
                while log_idx < len(tool_logs):
                    tl = tool_logs[log_idx]
                    # Tool log belongs to this assistant message if it was
                    # created at or before the assistant message timestamp
                    if tl["timestamp"] and msg_ts and tl["timestamp"] <= msg_ts:
                        msg["toolCalls"].append(
                            {
                                "id": tl["tool_call_id"],
                                "name": tl["tool_name"],
                                "args": _safe_json_parse(tl["tool_args"]),
                                "status": "success",
                                "output": (tl["tool_output"] or "")[:500],
                                "elapsed_ms": None,
                            }
                        )
                        log_idx += 1
                    else:
                        break

        emit(
            "thread_loaded",
            {
                "thread_id": thread_id,
                "messages": messages,
                "error": None,
            },
        )

    @socketio.on("request_context_window")
    def handle_request_context_window(data):
        """Return the actual content of each context window segment."""
        from agent.context_engineering import estimate_tokens
        from agent.system_prompt import AGENT_SYSTEM_PROMPT

        thread_id = data.get("thread_id", "")
        query = data.get("query", "")
        mm = _app_state["memory_manager"]

        segments = []

        # System Prompt
        segments.append(
            {
                "name": "System Prompt",
                "key": "system_prompt",
                "content": AGENT_SYSTEM_PROMPT,
                "tokens": estimate_tokens(AGENT_SYSTEM_PROMPT),
            }
        )

        # Conversation Memory
        try:
            conv = mm.read_conversational_memory(thread_id)
        except Exception as e:
            logger.warning("Failed to read conversation memory: %s", e)
            conv = "No prior conversation."
        segments.append(
            {
                "name": "Conversation",
                "key": "conversation",
                "content": conv,
                "tokens": estimate_tokens(conv),
            }
        )

        # Knowledge Base Memory
        try:
            kb = mm.read_knowledge_base(query) if query else "No query provided."
        except Exception as e:
            logger.warning("Failed to read knowledge base: %s", e)
            kb = "No relevant documents found."
        segments.append(
            {
                "name": "Knowledge Base",
                "key": "knowledge_base",
                "content": kb,
                "tokens": estimate_tokens(kb),
            }
        )

        # Workflow Memory
        try:
            wf = mm.read_workflow(query or "workflow", thread_id=thread_id)
        except Exception as e:
            logger.warning("Failed to read workflow memory: %s", e)
            wf = "No relevant workflows found."
        segments.append(
            {
                "name": "Workflows",
                "key": "workflows",
                "content": wf,
                "tokens": estimate_tokens(wf),
            }
        )

        # Toolbox Memory
        try:
            toolbox_results = mm.read_toolbox(query) if query else []
            if toolbox_results:
                tb_content = json.dumps(toolbox_results, indent=2)
            else:
                tb_content = "No semantically matched tools found."
        except Exception as e:
            logger.warning("Failed to read toolbox memory: %s", e)
            tb_content = "No tools available."
        segments.append(
            {
                "name": "Toolbox",
                "key": "toolbox",
                "content": tb_content,
                "tokens": estimate_tokens(tb_content),
            }
        )

        # Entity Memory
        try:
            ent = mm.read_entity(query or "entities", thread_id=thread_id)
        except Exception as e:
            logger.warning("Failed to read entity memory: %s", e)
            ent = "No entities found."
        segments.append(
            {
                "name": "Entities",
                "key": "entities",
                "content": ent,
                "tokens": estimate_tokens(ent),
            }
        )

        # Summary Memory
        try:
            summ = mm.read_summary_context(query or "", thread_id=thread_id)
        except Exception as e:
            logger.warning("Failed to read summary memory: %s", e)
            summ = "No summaries available."
        segments.append(
            {
                "name": "Summary Refs",
                "key": "summary_refs",
                "content": summ,
                "tokens": estimate_tokens(summ),
            }
        )

        total_tokens = sum(s["tokens"] for s in segments)

        emit(
            "context_window_update",
            {
                "thread_id": thread_id,
                "segments": segments,
                "total_tokens": total_tokens,
            },
        )

    @socketio.on("new_thread")
    def handle_new_thread(data):
        """Create a new empty thread."""
        thread_id = f"thread-{str(uuid.uuid4())[:8]}"
        emit("thread_created", {"thread_id": thread_id})

    @socketio.on("send_comparison")
    def handle_comparison(data):
        """Run query through both architectures, collecting per-tool latency."""
        from agent.comparison import run_comparison

        message = data.get("message", "")
        thread_id = data.get("thread_id", f"thread-{str(uuid.uuid4())[:8]}")

        if not message:
            emit("error", {"message": "Empty message"})
            return

        converged_conn = _app_state.get("converged_conn")
        converged_mm = _app_state.get("converged_memory_manager")
        sprawl_extra = _app_state.get("sprawl_extra")

        if not converged_conn or not sprawl_extra:
            emit(
                "comparison_complete",
                {
                    "error": "Both Oracle and sprawl databases must be running for comparison. "
                    "Start all database containers and restart the backend.",
                },
            )
            return

        _app_state["query_logger"].clear()

        result = run_comparison(
            query=message,
            thread_id=thread_id,
            converged_conn=converged_conn,
            sprawl_extra=sprawl_extra,
            embedding_model=_app_state["embedding_model"],
            converged_memory_manager=converged_mm,
            sprawl_memory_manager=_app_state["memory_manager"],
            llm_client=_app_state["llm_client"],
            query_logger=_app_state["query_logger"],
            socketio=_app_state["socketio"],
        )

        emit(
            "comparison_complete",
            {
                "thread_id": result["thread_id"],
                "response": result["response"],
                "latency_points": result["latency_points"],
                "total_converged_ms": result["total_converged_ms"],
                "total_sprawl_ms": result["total_sprawl_ms"],
                "converged_errors": result["converged_errors"],
                "sprawl_errors": result["sprawl_errors"],
                "tool_count": result["tool_count"],
            },
        )

    @socketio.on("health_check")
    def handle_health_check(data=None):
        """Check health of all sprawl database connections."""
        statuses = {}
        extra = _app_state.get("extra_connections") or _app_state.get("sprawl_extra") or {}

        # PostgreSQL
        pg = extra.get("pg_conn")
        if pg:
            t0 = time.time()
            try:
                cur = pg.cursor()
                cur.execute("SELECT 1")
                cur.fetchone()
                cur.close()
                statuses["postgresql"] = {
                    "status": "connected",
                    "latency_ms": round((time.time() - t0) * 1000, 1),
                }
            except Exception as e:
                statuses["postgresql"] = {"status": "error", "error": str(e)}
        else:
            statuses["postgresql"] = {"status": "not_configured"}

        # Neo4j
        neo4j = extra.get("neo4j_driver")
        if neo4j:
            t0 = time.time()
            try:
                with neo4j.session() as session:
                    session.run("RETURN 1").single()
                statuses["neo4j"] = {
                    "status": "connected",
                    "latency_ms": round((time.time() - t0) * 1000, 1),
                }
            except Exception as e:
                statuses["neo4j"] = {"status": "error", "error": str(e)}
        else:
            statuses["neo4j"] = {"status": "not_configured"}

        # MongoDB
        mongo = extra.get("mongo_db")
        if mongo:
            t0 = time.time()
            try:
                mongo.command("ping")
                statuses["mongodb"] = {
                    "status": "connected",
                    "latency_ms": round((time.time() - t0) * 1000, 1),
                }
            except Exception as e:
                statuses["mongodb"] = {"status": "error", "error": str(e)}
        else:
            statuses["mongodb"] = {"status": "not_configured"}

        # Qdrant
        qdrant = extra.get("qdrant_client")
        if qdrant:
            t0 = time.time()
            try:
                qdrant.get_collections()
                statuses["qdrant"] = {
                    "status": "connected",
                    "latency_ms": round((time.time() - t0) * 1000, 1),
                }
            except Exception as e:
                statuses["qdrant"] = {"status": "error", "error": str(e)}
        else:
            statuses["qdrant"] = {"status": "not_configured"}

        # Oracle (converged)
        oracle_conn = _app_state.get("converged_conn") or (
            _app_state.get("conn") if not extra else None
        )
        if oracle_conn:
            t0 = time.time()
            try:
                cur = oracle_conn.cursor()
                cur.execute("SELECT 1 FROM dual")
                cur.fetchone()
                cur.close()
                statuses["oracle"] = {
                    "status": "connected",
                    "latency_ms": round((time.time() - t0) * 1000, 1),
                }
            except Exception as e:
                statuses["oracle"] = {"status": "error", "error": str(e)}

        emit("health_check_result", statuses)


def _safe_json_parse(s):
    """Parse JSON string, returning empty dict on failure."""
    try:
        return json.loads(s) if s else {}
    except Exception:
        return {}
