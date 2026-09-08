"""Agent loop. The web-app version of §11.

Differences from the notebook:
  * `agent_turn` accepts a `socketio` reference and emits per-step events
    (`turn_started`, `tool_started`, `tool_finished`, `turn_finished`) so the
    front-end can render the trace live.
  * `build_context` includes the §11.5 skill manifest.
  * Returns a structured dict the API layer can serialize to the chat UI.
"""

from __future__ import annotations

import json
import time
from typing import Any

from config import (
    AGENT_ID, AGENT_BUDGET_SECONDS, AGENT_MAX_ITERATIONS, USER_ID,
    LLM_MODEL, LLM_MODEL_MAX_TOKENS,
)
from agent.llm import chat_with_retry
from agent.skills import build_skill_manifest
from agent.system_prompt import SYSTEM_PROMPT
from agent.tools import (
    TOOLS,
    retrieve_tools,
    set_request_identity,
    set_request_socket,
    set_request_thread_id,
)
from api.identities import referenced_tables
from memory.manager import get_or_create_thread


# Map duality view → underlying tables that get touched when the agent reads
# the view. Used by the tables_touched event emitter.
_DUALITY_TOUCHES = {
    "voyage_dv":  ["SUPPLYCHAIN.VOYAGES", "SUPPLYCHAIN.CONTAINERS",
                   "SUPPLYCHAIN.CARGO_ITEMS", "SUPPLYCHAIN.VESSELS",
                   "SUPPLYCHAIN.PORTS", "SUPPLYCHAIN.CARRIERS"],
    "vessel_dv":  ["SUPPLYCHAIN.VESSELS", "SUPPLYCHAIN.CARRIERS",
                   "SUPPLYCHAIN.VESSEL_POSITIONS"],
}


def _tables_touched_by(name: str, args: dict) -> tuple[list[str], str]:
    """Inspect a tool name + args and return (tables, action) it touches.

    `action` is one of: read, scan, write. Empty list when the tool doesn't
    touch a database table (e.g. exec_js, scratch_*, search_knowledge).
    """
    if name == "run_sql":
        sql = args.get("sql") or ""
        return sorted(referenced_tables(sql)), "read"
    if name == "scan_database":
        owner = (args.get("owner") or "").upper()
        # Scanning a schema reads every table in it; the front-end gets the
        # schema and pulses the tabs whose schema matches.
        return [f"{owner}.*"], "scan"
    if name in ("get_document", "query_documents"):
        view = args.get("view") or ""
        return _DUALITY_TOUCHES.get(view, []), "read"
    if name in ("scratch_write", "scratch_append"):
        return ["DBFS.scratchpad"], "write"
    if name == "scratch_read":
        return ["DBFS.scratchpad"], "read"
    return [], ""


def build_context(agent_conn, memory_client, thread_id: str, user_query: str,
                  identity=None) -> str:
    """Skill manifest + OAMP context card + retrieved schema facts + user query.

    When `identity` is provided the persona's clearance and any region/column
    restrictions are stamped at the top of the context so the model can explain
    *why* a given row was filtered or a given column came back redacted.
    """
    manifest = build_skill_manifest(agent_conn, user_query, k=3)

    thread = get_or_create_thread(memory_client, thread_id)
    try:
        card = thread.get_context_card(query=user_query)
        card_text = str(card) if card else ""
    except Exception:
        card_text = ""

    parts = []
    if identity is not None:
        regions = ", ".join(identity.regions) if identity.regions else "ALL"
        masks = ", ".join(identity.mask_cols) or "none"
        forbidden = ", ".join(identity.forbid_tables) or "none"
        parts.append(
            "--- Acting identity (Use As) ---\n"
            f"id: {identity.id}\n"
            f"label: {identity.label}\n"
            f"clearance: {identity.clearance}\n"
            f"authorized regions: {regions}\n"
            f"masked columns: {masks}\n"
            f"forbidden tables: {forbidden}\n"
            "If a query returns fewer rows than expected, or columns come back "
            "as [REDACTED], explain which clause of this identity caused it."
        )
    if manifest:
        parts.append(manifest.rstrip())
    if card_text:
        parts.append("--- Recent thread context ---")
        parts.append(card_text)
    parts.append("--- User question ---")
    parts.append(user_query)
    return "\n\n".join(parts)


def _emit(socketio, event: str, payload: dict, room: str | None = None) -> None:
    if socketio is None:
        return
    if room:
        socketio.emit(event, payload, room=room)
    else:
        socketio.emit(event, payload)


def _emit_token_usage(socketio, sid, resp, step: int, llm_client=None) -> None:
    """Pull `usage` off a ChatCompletion response and emit it to the client.

    OpenAI returns prompt_tokens / completion_tokens / total_tokens. OCI's
    OpenAI-compatible endpoint returns the same shape. If the provider omits
    usage we send zeros so the front-end's running totals stay consistent.

    `model` reflects the **active** provider's model at the time of the call —
    so if the LlmRouter has silently fallen back from OCI grok-4.3 to OpenAI
    gpt-5.5 (auth/404/network), the UI shows the model that actually served
    this turn, not the originally-configured one.
    """
    if socketio is None:
        return
    usage = getattr(resp, "usage", None)

    # Use the live router state when available; fall back to the static
    # LLM_MODEL constant if the caller didn't pass the client through.
    active_model = LLM_MODEL
    using_fallback = False
    if llm_client is not None and hasattr(llm_client, "info"):
        try:
            info = llm_client.info()
            active_model = info.get("active_model") or LLM_MODEL
            using_fallback = bool(info.get("using_fallback"))
        except Exception:
            pass

    payload = {
        "step": step,
        "prompt": getattr(usage, "prompt_tokens", 0) or 0,
        "completion": getattr(usage, "completion_tokens", 0) or 0,
        "total": getattr(usage, "total_tokens", 0) or 0,
        "model": active_model,
        "model_max": LLM_MODEL_MAX_TOKENS,
        "using_fallback": using_fallback,
    }
    _emit(socketio, "token_usage", payload, sid)


def agent_turn(
    *,
    user_query: str,
    thread_id: str,
    agent_conn,
    memory_client,
    llm_client,
    socketio=None,
    sid: str | None = None,
    identity=None,
    max_iterations: int = AGENT_MAX_ITERATIONS,
    budget_seconds: float = AGENT_BUDGET_SECONDS,
) -> dict[str, Any]:
    """Run one user turn. Returns the final answer plus a structured trace."""
    started = time.time()
    trace: list[dict[str, Any]] = []

    thread = get_or_create_thread(memory_client, thread_id)
    # OAMP runs memory extraction + context-summary refresh synchronously
    # inside add_messages when extract_memories=True. If the configured
    # extraction LLM rejects the request (bad key, wrong endpoint, etc.),
    # the failure should NOT take down the chat — log it and continue with
    # a degraded thread that just doesn't auto-extract.
    try:
        thread.add_messages([{"role": "user", "content": user_query}])
    except Exception as _oamp_err:
        print(f"[harness] OAMP add_messages(user) failed (extraction disabled "
              f"for this turn): {type(_oamp_err).__name__}: {str(_oamp_err)[:200]}")
    _emit(socketio, "turn_started", {
        "thread_id": thread_id, "user_query": user_query,
        "identity": identity.id if identity else None,
    }, sid)

    # Stash per-turn context so tools can read it without us threading every
    # value through every signature. Cleared in the finally below regardless
    # of how the loop terminates.
    set_request_identity(identity)
    set_request_thread_id(thread_id)
    set_request_socket(socketio, sid)
    try:
        return _run_turn_loop(
            user_query=user_query, thread_id=thread_id, agent_conn=agent_conn,
            memory_client=memory_client, llm_client=llm_client,
            socketio=socketio, sid=sid, identity=identity,
            max_iterations=max_iterations, budget_seconds=budget_seconds,
            started=started, trace=trace, thread=thread,
        )
    finally:
        set_request_identity(None)
        set_request_thread_id(None)
        set_request_socket(None, None)


def _run_turn_loop(
    *, user_query, thread_id, agent_conn, memory_client, llm_client,
    socketio, sid, identity, max_iterations, budget_seconds,
    started, trace, thread,
):
    context = build_context(agent_conn, memory_client, thread_id, user_query, identity)
    messages: list[dict] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": context},
    ]
    tool_schemas = retrieve_tools(user_query, k=6)

    final = ""
    for step in range(max_iterations):
        if time.time() - started > budget_seconds:
            trace.append({"type": "budget_exhausted", "step": step})
            break

        resp = chat_with_retry(llm_client, messages, tools=tool_schemas)
        msg = resp.choices[0].message

        # Surface token usage to the front-end so the right pane can show
        # how full the context window is, in real time as the loop runs.
        _emit_token_usage(socketio, sid, resp, step, llm_client=llm_client)

        if not msg.tool_calls:
            final = msg.content or ""
            trace.append({"type": "final_answer", "step": step, "content": final})
            break

        messages.append({
            "role": "assistant",
            "content": msg.content or "",
            "tool_calls": [
                {"id": tc.id, "type": "function",
                 "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                for tc in msg.tool_calls
            ],
        })

        for tc in msg.tool_calls:
            name = tc.function.name
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            _emit(socketio, "tool_started",
                  {"step": step, "tool_call_id": tc.id, "name": name, "args": args}, sid)

            touched, action = _tables_touched_by(name, args)
            if touched:
                _emit(socketio, "tables_touched", {
                    "step": step, "tool_call_id": tc.id, "name": name,
                    "tables": touched, "action": action,
                }, sid)

            if name not in TOOLS:
                output = json.dumps({"error": f"unknown tool: {name}"})
            else:
                fn, _schema = TOOLS[name]
                try:
                    output = fn(**args)
                except Exception as e:
                    output = json.dumps({"error": f"{type(e).__name__}: {e}"})

            # Offload full output to OAMP, truncate inlined preview.
            # NOTE: OAM.add_memory's first arg is `content` (positional or kw);
            # `memory=` is rejected as an unexpected kwarg.
            try:
                memory_client.add_memory(
                    output,
                    user_id=USER_ID, agent_id=AGENT_ID,
                    thread_id=thread_id,
                    metadata={
                        "kind": "tool_output", "tool_call_id": tc.id,
                        "tool_name": name, "tool_args": json.dumps(args)[:500],
                    },
                )
            except Exception as _e:
                print(f"[harness] add_memory(tool_output) failed: {type(_e).__name__}: {_e}")

            preview = (
                output if len(output) <= 600
                else output[:600] + f" ...[+{len(output)-600} bytes; "
                                    f"full: fetch_tool_output(tool_call_id='{tc.id}')]"
            )
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": preview})
            trace.append({
                "type": "tool", "step": step, "tool_call_id": tc.id,
                "name": name, "args": args, "preview": preview[:400],
            })
            _emit(socketio, "tool_finished",
                  {"step": step, "tool_call_id": tc.id, "name": name, "preview": preview[:400]}, sid)

    if not final:
        messages.append({"role": "user",
                         "content": "Budget exhausted. Provide your best answer now, no more tools."})
        resp = chat_with_retry(llm_client, messages, tools=None)
        _emit_token_usage(socketio, sid, resp, max_iterations, llm_client=llm_client)
        final = resp.choices[0].message.content or "(no answer produced)"
        trace.append({"type": "forced_finalize", "content": final})

    try:
        thread.add_messages([{"role": "assistant", "content": final}])
    except Exception as _oamp_err:
        print(f"[harness] OAMP add_messages(assistant) failed: "
              f"{type(_oamp_err).__name__}: {str(_oamp_err)[:200]}")

    # Episodic / conversational memory: store the user→assistant pair as a
    # semantically searchable memory so future turns can retrieve relevant past
    # conversations via search_knowledge (or the right-pane "Episodic" section).
    try:
        episode_body = f"User: {user_query}\n\nAssistant: {final}"
        memory_client.add_memory(
            episode_body,
            user_id=USER_ID, agent_id=AGENT_ID,
            thread_id=thread_id,
            metadata={
                "kind": "episodic",
                "thread_id": thread_id,
                "user_query": user_query[:240],
                "elapsed_seconds": round(time.time() - started, 2),
            },
        )
    except Exception as _e:
        print(f"[harness] episodic add_memory failed: {type(_e).__name__}: {_e}")

    elapsed = time.time() - started
    result = {
        "thread_id": thread_id,
        "answer": final,
        "trace": trace,
        "elapsed_seconds": round(elapsed, 2),
    }
    _emit(socketio, "turn_finished", result, sid)
    return result
