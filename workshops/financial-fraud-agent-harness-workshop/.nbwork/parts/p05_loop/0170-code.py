from workshop.loop import assistant_message, budgeted_steps, call_tool, end_turn, start_turn

def agent_turn(user_query, thread_id="default", max_iterations=8, budget_seconds=360.0, verbose=True):
    """Answer one question: alternate chat and call_tool until the model answers or the budget ends."""
    messages, tool_schemas, offload, started = start_turn(
        store, thread_id, user_query, SYSTEM_PROMPT, build_context, retrieve_tools, OFFLOAD_CHARS)
    final = ""
    for step in budgeted_steps(max_iterations, started, budget_seconds):
        msg = chat(messages, tools=tool_schemas).choices[0].message
        if not msg.tool_calls:      # the model answered: keep the text and stop looping
            final = msg.content or ""
            break
        # The model asked for tools. First record its request, so each tool result below follows its call.
        messages.append(assistant_message(msg))
        # TODO 8 (two lines): run each requested tool and add its result to the conversation. Write:
        #     for tc in msg.tool_calls:
        #         messages.append({"role": "tool", "tool_call_id": tc.id, "content": <the tool's result>})
        #   <the tool's result>  call_tool(TOOLS, tc, step, verbose, offload)   (runs the tool, returns its text)
        #   "tool_call_id": tc.id links the result to the request it answers.
        for tc in msg.tool_calls:
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": call_tool(TOOLS, tc, step, verbose, offload)})
    return end_turn(store, chat, thread_id, user_query, final, messages, started, verbose)
