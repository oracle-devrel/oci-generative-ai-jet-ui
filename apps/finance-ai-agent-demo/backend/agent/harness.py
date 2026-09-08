"""Turn-level agent harness: build context, run tool-call loop, persist results."""

import json
import time

import eventlet
from agent.context_engineering import calculate_context_usage, summarize_conversation_for_thread
from agent.system_prompt import AGENT_SYSTEM_PROMPT
from agent.tools import PRELOADED_TOOLS, create_tool_executor
from config import MAX_AGENT_EXECUTION_TIME_S, MAX_AGENT_ITERATIONS, OPENAI_MODEL

AUTO_COMPACT_THRESHOLD = 80  # percentage of context window that triggers auto-compaction


def _make_logger(socketio):
    """Create a log function that emits via WebSocket if available."""

    def _log(msg):
        ts = time.strftime("%H:%M:%S")
        line = f"[{ts}] [AGENT] {msg}"
        print(line, flush=True)
        if socketio:
            socketio.emit("app_log", {"line": line, "timestamp": ts})
            eventlet.sleep(0)

    return _log


def call_agent(
    query,
    thread_id,
    conn,
    embedding_model,
    memory_manager,
    llm_client,
    query_logger=None,
    socketio=None,
    max_iterations=None,
    max_execution_time_s=None,
    extra_connections=None,
):
    """Turn-level agent harness: build context -> streaming tool-call loop -> persist results."""
    _log = _make_logger(socketio)
    thread_id = str(thread_id)
    max_iterations = max_iterations or MAX_AGENT_ITERATIONS
    max_execution_time_s = max_execution_time_s or MAX_AGENT_EXECUTION_TIME_S
    steps = []
    start_time = time.time()
    current_message_id = f"msg-{int(time.time() * 1000)}"

    _log("--- New request ---")
    _log(f"Thread: {thread_id} | Query: {query[:80]}{'...' if len(query) > 80 else ''}")
    _log(f"Model: {OPENAI_MODEL} | Max iterations: {max_iterations}")

    # Create tool executor with injected dependencies
    execute_tool = create_tool_executor(
        conn,
        embedding_model,
        memory_manager,
        llm_client,
        query_logger,
        extra_connections=extra_connections,
    )

    # 1. BUILD CONTEXT (programmatic)
    def build_context():
        _log("Building context window...")
        ctx = f"# Question\n{query}\n\n"

        t0 = time.time()
        try:
            ctx += memory_manager.read_conversational_memory(thread_id) + "\n\n"
            _log(f"  Conversation memory loaded ({round((time.time()-t0)*1000)}ms)")
        except Exception as e:
            ctx += "## Conversation Memory\nNo prior conversation.\n\n"
            _log(f"  Conversation memory: empty ({e})")

        t0 = time.time()
        try:
            ctx += memory_manager.read_knowledge_base(query) + "\n\n"
            _log(f"  Knowledge base loaded ({round((time.time()-t0)*1000)}ms)")
        except Exception as e:
            ctx += "## Knowledge Base Memory\nNo relevant documents found.\n\n"
            _log(f"  Knowledge base: empty ({e})")

        t0 = time.time()
        try:
            ctx += memory_manager.read_workflow(query, thread_id=thread_id) + "\n\n"
            _log(f"  Workflow memory loaded ({round((time.time()-t0)*1000)}ms)")
        except Exception as e:
            ctx += "## Workflow Memory\nNo relevant workflows found.\n\n"
            _log(f"  Workflow memory: empty ({e})")

        t0 = time.time()
        try:
            ctx += memory_manager.read_entity(query, thread_id=thread_id) + "\n\n"
            _log(f"  Entity memory loaded ({round((time.time()-t0)*1000)}ms)")
        except Exception as e:
            ctx += "## Entity Memory\nNo entities found.\n\n"
            _log(f"  Entity memory: empty ({e})")

        t0 = time.time()
        try:
            ctx += memory_manager.read_summary_context(query, thread_id=thread_id) + "\n\n"
            _log(f"  Summary memory loaded ({round((time.time()-t0)*1000)}ms)")
        except Exception as e:
            ctx += "## Summary Memory\nNo summaries available.\n\n"
            _log(f"  Summary memory: empty ({e})")

        _log(f"Context built: {len(ctx)} chars ({round((time.time()-start_time)*1000)}ms total)")
        return ctx

    context = build_context()

    # 1a. AUTO-COMPACTION: if context >= 80%, compact before proceeding
    usage = calculate_context_usage(context)
    _log(f"Context usage: {usage['percent']}% ({usage['tokens']}/{usage['max']} tokens)")
    if usage["percent"] >= AUTO_COMPACT_THRESHOLD:
        _log(f"AUTO-COMPACT triggered ({usage['percent']}% >= {AUTO_COMPACT_THRESHOLD}%)")
        try:
            compact_result = summarize_conversation_for_thread(
                thread_id, memory_manager, llm_client
            )
            _log(
                f"  Compacted {compact_result.get('messages_compacted', 0)} messages -> summary {compact_result.get('id', '?')}"
            )
            # Rebuild context with compacted conversation
            context = build_context()
            usage = calculate_context_usage(context)
            _log(
                f"  Context after compaction: {usage['percent']}% ({usage['tokens']}/{usage['max']} tokens)"
            )
            if socketio:
                socketio.emit("token_usage_update", usage)
                eventlet.sleep(0)
        except Exception as e:
            _log(f"  Auto-compaction failed (continuing with full context): {e}")

    # 1b. TOOL ASSEMBLY: dynamic (augmented from TOOLBOX_MEMORY) + preloaded fallback
    _log("Assembling tools...")
    t0 = time.time()

    # Prefer augmented tools from TOOLBOX_MEMORY (richer descriptions for the LLM)
    dynamic_tools = []
    dynamic_names = set()
    try:
        retrieved = memory_manager.read_toolbox(query, k=7)
        for t in retrieved:
            name = t["function"]["name"]
            if name not in dynamic_names:
                dynamic_tools.append(t)
                dynamic_names.add(name)
        _log(f"  Augmented tools retrieved: {sorted(dynamic_names)}")
    except Exception as e:
        _log(f"  Dynamic tool retrieval failed (using preloaded only): {e}")

    # Backfill with preloaded tools for any that weren't retrieved
    for t in PRELOADED_TOOLS:
        name = t["function"]["name"]
        if name not in dynamic_names:
            dynamic_tools.append(t)
            dynamic_names.add(name)

    tool_names = [t["function"]["name"] for t in dynamic_tools]
    _log(
        f"  Tools selected ({len(dynamic_tools)}): {tool_names} ({round((time.time()-t0)*1000)}ms)"
    )

    # 2. STORE USER MESSAGE (programmatic)
    _log("Storing user message...")
    memory_manager.write_conversational_memory(query, "user", thread_id)
    try:
        memory_manager.write_entity(
            "", "", "", llm_client=llm_client, text=query, thread_id=thread_id
        )
    except Exception as e:
        _log(f"  Entity extraction for user message failed: {e}")

    # 3. STREAMING TOOL-CALL LOOP
    messages = [
        {"role": "system", "content": AGENT_SYSTEM_PROMPT},
        {"role": "user", "content": context},
    ]
    final_answer = ""

    _log(f"Starting Agent Loop (model={OPENAI_MODEL})...")

    for iteration in range(max_iterations):
        elapsed = time.time() - start_time
        if elapsed > max_execution_time_s:
            _log(f"TIMEOUT after {round(elapsed, 1)}s")
            break

        _log(f"Iteration {iteration + 1}/{max_iterations} ({round(elapsed, 1)}s elapsed)")

        try:
            llm_start = time.time()
            response = llm_client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=messages,
                tools=dynamic_tools,
                tool_choice="auto",
                stream=True,
            )
            _log(f"  LLM request sent ({round((time.time()-llm_start)*1000)}ms to first chunk)")
        except Exception as e:
            _log(f"  LLM ERROR: {e}")
            final_answer = f"Error calling LLM: {e}"
            break

        # Accumulate streaming response
        accumulated_content = ""
        accumulated_tool_calls = []
        chunk_count = 0

        for chunk in response:
            choice = chunk.choices[0]
            delta = choice.delta
            chunk_count += 1

            # Stream text content to client token-by-token
            if delta.content:
                accumulated_content += delta.content
                if socketio:
                    socketio.emit(
                        "response_chunk",
                        {
                            "chunk": delta.content,
                            "message_id": current_message_id,
                        },
                    )
                    eventlet.sleep(0)

            # Accumulate tool call deltas
            if delta.tool_calls:
                for tc_delta in delta.tool_calls:
                    idx = tc_delta.index
                    while idx >= len(accumulated_tool_calls):
                        accumulated_tool_calls.append(
                            {
                                "id": "",
                                "type": "function",
                                "function": {"name": "", "arguments": ""},
                            }
                        )
                    if tc_delta.id:
                        accumulated_tool_calls[idx]["id"] = tc_delta.id
                    if tc_delta.function:
                        if tc_delta.function.name:
                            accumulated_tool_calls[idx]["function"][
                                "name"
                            ] += tc_delta.function.name
                        if tc_delta.function.arguments:
                            accumulated_tool_calls[idx]["function"][
                                "arguments"
                            ] += tc_delta.function.arguments

        _log(
            f"  Stream complete: {chunk_count} chunks, {len(accumulated_content)} chars, {len(accumulated_tool_calls)} tool calls"
        )

        if accumulated_tool_calls:
            # Append assistant message with tool calls
            messages.append(
                {
                    "role": "assistant",
                    "content": accumulated_content or None,
                    "tool_calls": accumulated_tool_calls,
                }
            )

            for tc_data in accumulated_tool_calls:
                tool_name = tc_data["function"]["name"]
                raw_args = tc_data["function"]["arguments"] or "{}"
                try:
                    tool_args = json.loads(raw_args)
                except Exception:
                    tool_args = {}

                tc_id = tc_data["id"]
                _log(f"  TOOL CALL: {tool_name}({json.dumps(tool_args)[:100]})")

                # Emit tool_call_start
                if socketio:
                    socketio.emit(
                        "tool_call_start",
                        {
                            "tool_call_id": tc_id,
                            "tool_name": tool_name,
                            "tool_args": tool_args,
                            "message_id": current_message_id,
                        },
                    )
                    eventlet.sleep(0)

                # Execute the tool
                tool_start = time.time()
                try:
                    result = execute_tool(tool_name, tool_args)
                    tool_elapsed = round((time.time() - tool_start) * 1000, 1)
                    steps.append(
                        f"{tool_name}({', '.join(f'{k}={v}' for k, v in tool_args.items())}) -> success"
                    )
                    _log(f"  TOOL OK: {tool_name} -> {tool_elapsed}ms | {str(result)[:100]}...")

                    if socketio:
                        socketio.emit(
                            "tool_call_complete",
                            {
                                "tool_call_id": tc_id,
                                "tool_name": tool_name,
                                "output": str(result)[:2000],
                                "elapsed_ms": tool_elapsed,
                                "status": "success",
                            },
                        )
                        eventlet.sleep(0)
                except Exception as e:
                    result = f"Error: {e}"
                    tool_elapsed = round((time.time() - tool_start) * 1000, 1)
                    steps.append(f"{tool_name} -> failed: {e}")
                    _log(f"  TOOL FAIL: {tool_name} -> {tool_elapsed}ms | {e}")

                    if socketio:
                        socketio.emit(
                            "tool_call_complete",
                            {
                                "tool_call_id": tc_id,
                                "tool_name": tool_name,
                                "output": str(e),
                                "elapsed_ms": tool_elapsed,
                                "status": "error",
                            },
                        )
                        eventlet.sleep(0)

                # Log tool output and use compact reference in context
                compact_ref = memory_manager.write_tool_log(
                    thread_id, tc_id, tool_name, json.dumps(tool_args), str(result)
                )
                messages.append({"role": "tool", "tool_call_id": tc_id, "content": compact_ref})
        else:
            # No tool calls -> final answer (already streamed)
            final_answer = accumulated_content
            _log(f"  Final answer received ({len(final_answer)} chars)")
            break

    # 4. GUARDED STOP (if budget exceeded, force final answer)
    if not final_answer:
        _log("Budget exceeded, forcing final answer...")
        try:
            final_messages = messages + [
                {
                    "role": "user",
                    "content": "Finalize your answer using the context and tool outputs so far. Do not call tools.",
                }
            ]
            final_resp = llm_client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=final_messages,
                stream=True,
            )
            for chunk in final_resp:
                delta = chunk.choices[0].delta
                if delta.content:
                    final_answer += delta.content
                    if socketio:
                        socketio.emit(
                            "response_chunk",
                            {
                                "chunk": delta.content,
                                "message_id": current_message_id,
                            },
                        )
                        eventlet.sleep(0)
        except Exception as e:
            final_answer = f"Error finalizing answer: {e}"
            _log(f"Finalization ERROR: {e}")

    # 5. SAVE RESULTS (programmatic)
    _log("Saving results...")
    if steps:
        try:
            memory_manager.write_workflow(query, steps, final_answer, thread_id=thread_id)
        except Exception as e:
            _log(f"  Workflow save failed: {e}")
    try:
        memory_manager.write_entity(
            "", "", "", llm_client=llm_client, text=final_answer, thread_id=thread_id
        )
    except Exception as e:
        _log(f"  Entity extraction for response failed: {e}")
    memory_manager.write_conversational_memory(final_answer, "assistant", thread_id)

    total_elapsed = round(time.time() - start_time, 2)
    _log(
        f"DONE: {len(steps)} tool calls, {total_elapsed}s total, {len(final_answer)} chars response"
    )
    _log("---")

    return {
        "response": final_answer,
        "thread_id": thread_id,
        "message_id": current_message_id,
        "steps": steps,
        "elapsed_s": total_elapsed,
    }
