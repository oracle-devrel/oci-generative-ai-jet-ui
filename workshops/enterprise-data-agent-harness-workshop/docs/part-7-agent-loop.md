# Part 7: The Agent Loop

Everything we'''ve built so far is plumbing. **This** is the agent. Read this section twice.

## The Loop in One Sentence

```
build_context  →  call LLM with retrieved tools  →  if tool_calls: dispatch  else: final answer  →  log
```

Every turn assembles a context block from OAMP + retrieved schema facts, calls the chat LLM with the top-k tools surfaced from the toolbox, and either dispatches the tool calls the model emitted or breaks out with the model'''s natural-language answer. The whole thing is roughly 90 lines of Python.

## What `build_context` Stacks Together

`build_context(thread_id, user_query)` is **pre-built**. It assembles three layers into one user message:

1. **Skill manifest** (top-3 from the skillbox, formatted as one line per skill) — gives the model a menu of relevant playbooks it can `load_skill` on demand.
2. **OAMP context card** — relevant memories from this thread, including the rolling LLM-written summary if `enable_context_summary=True` (it is, in this workshop).
3. **Institutional knowledge top-k** — the result of `retrieve_knowledge(user_query, k=3)` formatted as bullet points.

The user'''s actual question is appended at the end. The model sees one cohesive user message, not three concatenated blocks.

## The System Prompt — Read It Carefully

The pre-built `SYSTEM_PROMPT` is the agent'''s job description. It tells the model:

1. **Always call `search_knowledge` first** — paraphrase the user'''s question, retrieve relevant facts, then pick tables.
2. **Stay read-only** — `run_sql` rejects DDL/DML; the prompt reinforces that.
3. **For numeric work, use `exec_js`** — never compute percentiles or weighted means in your head.
4. **For non-trivial SQL, use the scratchpad** — `scratch_write` the draft, `scratch_read` it back before passing to `run_sql`.
5. **Call `remember` for corrections.** The user telling you "TEU is in 20-foot equivalents" is institutional knowledge — persist it.
6. **Never fabricate a table or column.** When unsure, scan or say so.

These are the rules that turn a model into an *agent* — without them, GPT-class models often skip the JS hop, compute aggregates in their head, and confidently quote wrong numbers.

## TODO 5: Implement `agent_turn`

This is the heart of the harness. Spend time on it — once you understand `agent_turn`, you understand the whole workshop.

The function takes a user query, a thread id, and budgets. It returns the model'''s final answer.

The skeleton with `# YOUR CODE` markers:

```python
def agent_turn(user_query: str, thread_id: str = "default",
               max_iterations: int = 8, budget_seconds: float = 360.0,
               verbose: bool = True) -> str:
    started = time.time()
    log_message(thread_id, "user", user_query)

    # 1. Build the context block + retrieve top-k tool schemas.
    context = build_context(thread_id, user_query)
    messages: list[dict] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user",   "content": context},
    ]
    tool_schemas = retrieve_tools(user_query, k=6)

    # 2. The loop — at most max_iterations rounds, capped by wall-clock budget.
    final = ""
    step = 0
    for step in range(max_iterations):
        if time.time() - started > budget_seconds:
            if verbose: print(f"  ! budget exhausted at iteration {step}")
            break

        # YOUR CODE: call the LLM with the messages + tool schemas
        # YOUR CODE: if no tool_calls, set final = msg.content and break
        # YOUR CODE: otherwise, append the assistant'''s tool_calls message and dispatch each tool

    # 3. If we exhausted the budget, force a final answer (no tools).
    if not final:
        messages.append({"role": "user",
                         "content": "Budget exhausted. Provide your best answer now, no more tools."})
        resp = chat(messages, tools=None)
        final = resp.choices[0].message.content or "(no answer produced)"

    log_message(thread_id, "assistant", final)
    return final
```

**The dispatch pattern you need to fill in:**

```python
resp = chat(messages, tools=tool_schemas)
msg = resp.choices[0].message

if not msg.tool_calls:
    final = msg.content or ""
    if verbose: print(f"  step {step}: final answer")
    break

# Append the assistant'''s tool_calls message verbatim — the LLM expects
# its own tool_calls to be echoed back so it can match each tool result
# to the call that produced it.
messages.append({
    "role": "assistant",
    "content": msg.content or "",
    "tool_calls": [
        {"id": tc.id, "type": "function",
         "function": {"name": tc.function.name,
                      "arguments": tc.function.arguments}}
        for tc in msg.tool_calls
    ],
})

# Dispatch each tool the model asked for.
for tc in msg.tool_calls:
    name = tc.function.name
    try:
        args = json.loads(tc.function.arguments or "{}")
    except json.JSONDecodeError:
        args = {}
    if verbose: print(f"  step {step}: -> {name}({args})")

    if name not in TOOLS:
        output = json.dumps({"error": f"unknown tool: {name}"})
    else:
        fn, _ = TOOLS[name]
        try:
            output = fn(**args)
        except Exception as e:
            output = json.dumps({"error": f"{type(e).__name__}: {e}"})

    # Append the tool result so the next LLM iteration sees it.
    messages.append({"role": "tool", "tool_call_id": tc.id, "content": output})
```

The key invariant: **after each tool dispatch, the message list has the assistant'''s tool_calls *and* the corresponding tool results in the same order.** OpenAI'''s API requires this — drop a `tool` message and the next `chat(...)` call raises a 400.

The complete solution is in `notebook_complete.ipynb`. Use it after you'''ve made a real attempt — copy-pasting before you'''ve thought about the dispatch flow defeats the purpose.

## Why Both Budgets

```python
for step in range(max_iterations):
    if time.time() - started > budget_seconds:
        break
```

**Iteration count alone** lets a fast model burn money — 8 iterations of `gpt-5.5` is cheap; 8 iterations of an unconstrained agent calling `scan_database` on a 10,000-table production schema is not.

**Wall-clock alone** lets a slow LLM stall the cell. A reasoning-heavy model can take 30+ seconds per call; without an iteration cap, a single chat round-trip can chew the entire budget.

Use both, every loop.

## The "Forced Final Answer" Pattern

If the loop exits without setting `final` (budget exhausted, max iterations hit), we make one more LLM call — this time **without tools**:

```python
messages.append({"role": "user",
                 "content": "Budget exhausted. Provide your best answer now, no more tools."})
resp = chat(messages, tools=None)
final = resp.choices[0].message.content or "(no answer produced)"
```

This guarantees the user gets *some* answer, even if the agent didn'''t converge. Without this guard, a runaway agent leaves the user with an empty string. Worse — it leaves them with no signal that something went wrong.

## The three-turn end-to-end demo (just run)

Once `agent_turn` is implemented, run a 3-turn conversation on a single thread. Each turn is designed to exercise a different harness component:

1. **Turn 1 — discovery.** *"What'''s in the SUPPLYCHAIN schema? Briefly — list the entities and how they relate."* Forces `search_knowledge` over scanned facts.
2. **Turn 2 — live data.** *"How many active voyages does each carrier have?"* Forces `run_sql`.
3. **Turn 3 — correction + persistence.** *"Important: `cargo_items.unit_value_cents` is always USD CENTS, never dollars. Save this as a correction by calling `remember` BEFORE you respond."* Forces `remember` and creates a persisted correction memory.

**Solution:**

```python
thread = "demo-session-1"

q1 = "What'''s in the SUPPLYCHAIN schema? Briefly — list the entities and how they relate."
print("USER:", q1)
print("ASSISTANT:", agent_turn(q1, thread_id=thread))

q2 = "How many active voyages does each carrier currently have? Show me a small table sorted by count desc."
print("\nUSER:", q2)
print("ASSISTANT:", agent_turn(q2, thread_id=thread))

q3 = ("Important: in the SUPPLYCHAIN schema, cargo_items.unit_value_cents is always USD CENTS, never dollars. "
      "Save this as a '"'"'correction'"'"' memory by calling the remember tool BEFORE you respond, "
      "then confirm.")
print("\nUSER:", q3)
print("ASSISTANT:", agent_turn(q3, thread_id=thread))
```

After Turn 3, query the OAMP store and you'''ll see a new memory with `metadata.kind = "correction"`. From now on, asking about cargo values triggers `search_knowledge` and the correction surfaces — the agent has *learned*.

## Key Takeaways — Part 7

- **The whole agent is ~90 lines.** `build_context → call LLM → if tool_calls dispatch else final → log`. No framework. Read `agent_turn` once and you understand the entire control flow.
- **Both budgets matter.** Iteration count alone lets a fast model burn money; wall-clock alone lets a slow LLM stall the cell. Use both, every loop.
- **Persistence between turns is what makes it an agent, not a chat.** Conversation history, tool outputs, schema facts, corrections — all of it survives in Oracle and reappears via the context card on the next turn.
- **A correction at turn N changes the answer at turn N+1.** The `remember` tool writes to the same OAMP store the agent retrieves from — no separate "training" step, no model fine-tune, no app deploy.

## Troubleshooting

**`openai.BadRequestError: 400 ... messages with role '"'"'tool'"'"' must be a response to a preceding message with '"'"'tool_calls'"'"'`** — You appended a tool result without first appending the assistant'''s `tool_calls` message. Always append the assistant message *first*, then the tool results, in order.

**Loop never terminates** — Verify your `for step in range(max_iterations):` actually `break`s when `msg.tool_calls` is empty. A common bug is forgetting the `break` after setting `final`.

**`KeyError` in `TOOLS[name]`** — The model emitted a tool name you didn'''t register. The dispatch handles this with `if name not in TOOLS: output = json.dumps({"error": ...})` — make sure that check is in your loop.

**Agent calls the same tool with the same args repeatedly** — This is a real pathology of GPT-class models. The complete solution adds a 3-deep `recent_calls` dedupe; you don'''t need it for the workshop demo, but in production it'''s cheap insurance.
