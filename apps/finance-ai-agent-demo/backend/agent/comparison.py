"""Comparison mode: runs the same agent query through both architectures and collects latency."""

import json
import time

import eventlet
from agent.system_prompt import AGENT_SYSTEM_PROMPT
from agent.tools import PRELOADED_TOOLS, create_tool_executor
from config import MAX_AGENT_EXECUTION_TIME_S, MAX_AGENT_ITERATIONS, OPENAI_MODEL


def run_comparison(
    query,
    thread_id,
    converged_conn,
    sprawl_extra,
    embedding_model,
    converged_memory_manager,
    sprawl_memory_manager,
    llm_client,
    query_logger=None,
    socketio=None,
):
    """Run the same query through both architectures, collecting per-step latency.

    Instead of running two full agent loops (expensive + nondeterministic tool choices),
    we run ONE agent loop to determine which tools to call and with what args, then
    replay those exact tool calls against both backends, timing each one.
    """
    _log = _make_logger(socketio)
    thread_id = str(thread_id)
    _log("=== COMPARISON MODE ===")
    _log(f"Query: {query[:80]}")

    # Build converged tool executor
    converged_executor = create_tool_executor(
        converged_conn,
        embedding_model,
        converged_memory_manager,
        llm_client,
        query_logger=None,  # no logging for converged benchmark
    )

    # Build sprawl tool executor
    from agent.sprawl_tools import (
        check_compliance_sprawl,
        convergent_search_sprawl,
        find_nearby_clients_sprawl,
        find_similar_accounts_sprawl,
        get_account_details_sprawl,
        get_investment_preferences_sprawl,
        get_portfolio_risk_sprawl,
        search_compliance_rules_sprawl,
        search_knowledge_base_sprawl,
    )

    sprawl_pg = sprawl_extra.get("pg_conn")
    sprawl_neo4j = sprawl_extra.get("neo4j_driver")
    sprawl_qdrant = sprawl_extra.get("qdrant_client")

    sprawl_tool_map = {
        "get_account_details": lambda args: get_account_details_sprawl(sprawl_pg, args, None),
        "get_portfolio_risk": lambda args: get_portfolio_risk_sprawl(sprawl_pg, args, None),
        "check_compliance": lambda args: check_compliance_sprawl(sprawl_pg, args, None),
        "find_similar_accounts": lambda args: find_similar_accounts_sprawl(
            sprawl_neo4j, sprawl_pg, args, None
        ),
        "search_knowledge_base": lambda args: search_knowledge_base_sprawl(
            sprawl_qdrant, embedding_model, sprawl_pg, args, None
        ),
        "get_investment_preferences": lambda args: get_investment_preferences_sprawl(
            sprawl_pg, args, None
        ),
        "search_compliance_rules": lambda args: search_compliance_rules_sprawl(
            sprawl_pg, args, None
        ),
        "find_nearby_clients": lambda args: find_nearby_clients_sprawl(sprawl_pg, args, None),
        "convergent_search": lambda args: convergent_search_sprawl(
            sprawl_pg, sprawl_neo4j, sprawl_qdrant, embedding_model, args, None
        ),
    }

    # Phase 1: Run agent loop to determine tool calls (use converged as primary)
    _log("Phase 1: Running agent to determine tool calls...")
    messages = [
        {"role": "system", "content": AGENT_SYSTEM_PROMPT},
        {"role": "user", "content": f"# Question\n{query}"},
    ]

    tool_calls_to_replay = []
    final_answer = ""
    start = time.time()

    for _iteration in range(min(MAX_AGENT_ITERATIONS, 5)):
        if time.time() - start > MAX_AGENT_EXECUTION_TIME_S:
            break

        try:
            response = llm_client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=messages,
                tools=PRELOADED_TOOLS,
                tool_choice="auto",
                stream=True,
            )
        except Exception as e:
            _log(f"LLM error: {e}")
            final_answer = f"Error: {e}"
            break

        content = ""
        acc_tool_calls = []
        for chunk in response:
            delta = chunk.choices[0].delta
            if delta.content:
                content += delta.content
            if delta.tool_calls:
                for tc in delta.tool_calls:
                    idx = tc.index
                    while idx >= len(acc_tool_calls):
                        acc_tool_calls.append({"id": "", "function": {"name": "", "arguments": ""}})
                    if tc.id:
                        acc_tool_calls[idx]["id"] = tc.id
                    if tc.function:
                        if tc.function.name:
                            acc_tool_calls[idx]["function"]["name"] += tc.function.name
                        if tc.function.arguments:
                            acc_tool_calls[idx]["function"]["arguments"] += tc.function.arguments

        if acc_tool_calls:
            messages.append(
                {
                    "role": "assistant",
                    "content": content or None,
                    "tool_calls": [
                        {"id": tc["id"], "type": "function", "function": tc["function"]}
                        for tc in acc_tool_calls
                    ],
                }
            )

            for tc in acc_tool_calls:
                name = tc["function"]["name"]
                try:
                    args = json.loads(tc["function"]["arguments"] or "{}")
                except Exception:
                    args = {}

                # Skip non-DB tools from benchmarking
                if name in ("expand_summary", "summarize_conversation", "search_tavily"):
                    result = converged_executor(name, args)
                    messages.append(
                        {"role": "tool", "tool_call_id": tc["id"], "content": str(result)[:1500]}
                    )
                    continue

                tool_calls_to_replay.append({"name": name, "args": args, "tool_call_id": tc["id"]})
                # Execute on converged for the agent loop to continue
                result = converged_executor(name, args)
                messages.append(
                    {"role": "tool", "tool_call_id": tc["id"], "content": str(result)[:1500]}
                )
        else:
            final_answer = content
            break

    if not final_answer:
        try:
            resp = llm_client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=messages
                + [{"role": "user", "content": "Finalize your answer. Do not call tools."}],
            )
            final_answer = resp.choices[0].message.content or ""
        except Exception:
            final_answer = "Could not finalize answer."

    _log(f"Phase 1 complete: {len(tool_calls_to_replay)} tool calls to benchmark")

    # Phase 2: Replay tool calls against BOTH backends, timing each
    _log("Phase 2: Benchmarking tool calls against both architectures...")
    latency_points = []

    for tc in tool_calls_to_replay:
        name = tc["name"]
        args = tc["args"]
        point = {"tool": name, "args": args}

        # Converged timing
        t0 = time.time()
        converged_error = None
        try:
            converged_executor(name, args)
        except Exception as e:
            converged_error = str(e)
        point["converged_ms"] = round((time.time() - t0) * 1000, 1)
        point["converged_error"] = converged_error

        # Sprawl timing (sequential — this is the real cost)
        t0 = time.time()
        sprawl_error = None
        try:
            if name in sprawl_tool_map:
                sprawl_tool_map[name](args)
            else:
                sprawl_error = f"No sprawl implementation for {name}"
        except Exception as e:
            sprawl_error = str(e)
        point["sprawl_ms"] = round((time.time() - t0) * 1000, 1)
        point["sprawl_error"] = sprawl_error

        latency_points.append(point)

        _log(
            f"  {name}: converged={point['converged_ms']}ms  sprawl={point['sprawl_ms']}ms"
            f"{'  [C-ERR]' if converged_error else ''}"
            f"{'  [S-ERR]' if sprawl_error else ''}"
        )

        # Emit incremental point
        if socketio:
            socketio.emit("comparison_latency_point", point)
            eventlet.sleep(0)

    # Cumulative totals
    total_converged = sum(p["converged_ms"] for p in latency_points)
    total_sprawl = sum(p["sprawl_ms"] for p in latency_points)
    converged_errors = sum(1 for p in latency_points if p.get("converged_error"))
    sprawl_errors = sum(1 for p in latency_points if p.get("sprawl_error"))

    _log("=== COMPARISON COMPLETE ===")
    _log(f"Total converged: {total_converged}ms | Total sprawl: {total_sprawl}ms")
    _log(f"Converged errors: {converged_errors} | Sprawl errors: {sprawl_errors}")

    return {
        "response": final_answer,
        "thread_id": thread_id,
        "latency_points": latency_points,
        "total_converged_ms": total_converged,
        "total_sprawl_ms": total_sprawl,
        "converged_errors": converged_errors,
        "sprawl_errors": sprawl_errors,
        "tool_count": len(latency_points),
    }


def _make_logger(socketio):
    def _log(msg):
        ts = time.strftime("%H:%M:%S")
        line = f"[{ts}] [COMPARE] {msg}"
        print(line, flush=True)
        if socketio:
            socketio.emit("app_log", {"line": line, "timestamp": ts})
            eventlet.sleep(0)

    return _log
