# Part 11: Tool-Output Offload

The Part 7 `agent_turn` inlines every tool result verbatim into the next message. That's fine for short outputs but **blows the context window** on a 50-row `run_sql`, a multi-KB skill body, or a long `exec_js` log. Part 11 fixes that.

## The pattern

Three glued-together pieces:

1. **`log_tool`** — every dispatch persists the full output as an OAMP memory tagged `kind=tool_output` with the LLM's `tool_call_id`.
2. **Truncation marker** — outputs over 600 bytes are replaced in the message list with a compact preview ending in `...[+N bytes. full output: fetch_tool_output(tool_call_id='call_…')]`. The model knows where to find the rest.
3. **`fetch_tool_output(tool_call_id)`** — a registered tool that recovers the full bytes by id when the agent decides it needs them.

Pieces 1 and 3 are your **TODO 8** and **TODO 9**. Piece 2 (the `agent_turn` redefinition with the truncation marker) is the pre-built cell at the end of Part 11 — re-run cell §11's `agent_turn` to revert to the minimal version.

## The math

A 50-row `run_sql` of `cargo_items` is ~10 KB. A `skillbox` body for `agent/ora-error-catalog` is ~25 KB. Three of those in one turn and you're at 100 KB of context for outputs the model only skimmed once.

After offload + truncation:

- Each output is **600 bytes inline** (the preview).
- The model gets a `fetch_tool_output(tool_call_id=...)` hint when truncation happens.
- The full bytes live in OAMP, retrievable on demand.

Most truncated outputs are **never refetched** — the model only pulls full bytes when its preview isn't enough. Bandwidth follows attention.

## TODO 8: Implement `log_tool`

The write side of offload. Every dispatch persists the **full** tool output as an OAMP memory tagged `kind=tool_output` with the LLM's `tool_call_id`.

**Solution:**

```python
def log_tool(thread_id, tool_call_id, tool_name, tool_args, tool_output):
    memory_client.add_memory(
        tool_output,
        user_id=USER_ID, agent_id=AGENT_ID,
        thread_id=thread_id,
        metadata={
            "kind": "tool_output",
            "tool_call_id": tool_call_id,
            "tool_name": tool_name,
            "tool_args": json.dumps(tool_args),
        },
    )
```

The metadata shape isn't optional — TODO 9 (`tool_fetch_tool_output`) looks rows up by `metadata_filter={"kind": "tool_output", "tool_call_id": ...}`, so the keys here must match. `tool_args` is JSON-serialised so OAMP's metadata store (a JSON column) can index it without a custom encoder for whatever Python types the caller passed in.

The hard-stop assert below your implementation calls `log_tool` with a synthetic `tool_call_id`, then queries OAMP with the same metadata filter and checks the row came back with the right shape.

## TODO 9: Register `tool_fetch_tool_output`

The read side, mirror image of TODO 8. The agent calls this when its inlined preview was truncated and it needs the missing bytes to answer.

The lookup uses OAMP's `metadata_filter`:

```python
records = memory_client._store.list(
    "memory",
    user_id=USER_ID, agent_id=AGENT_ID,
    metadata_filter={"kind": "tool_output", "tool_call_id": tool_call_id},
    limit=1,
)
```

Return a JSON object with `tool_name`, `tool_args`, and `tool_output` if found, or `{"error": ...}` if no record matches.

**Solution:**

```python
@register
def tool_fetch_tool_output(tool_call_id: str) -> str:
    """Retrieve the full, untruncated output of a previous tool call.
    Use this when a prior tool result in your context was truncated with
    '...[+N bytes. full output: fetch_tool_output(tool_call_id=...)]' and you need
    the missing bytes to answer.
    """
    records = memory_client._store.list(
        "memory",
        user_id=USER_ID, agent_id=AGENT_ID,
        metadata_filter={"kind": "tool_output", "tool_call_id": tool_call_id},
        limit=1,
    )
    if not records:
        return json.dumps({"error": f"no tool call with id {tool_call_id}"})
    r = records[0]
    meta = r.metadata or {}
    return json.dumps({
        "tool_name":   meta.get("tool_name"),
        "tool_args":   meta.get("tool_args"),
        "tool_output": r.content,
    })
```

After this is registered, the pre-built `agent_turn` redefinition in the next cell calls `log_tool` for each dispatch and emits the truncation marker.

## What changes in `agent_turn`

The Part 7 `agent_turn` had this dispatch tail:

```python
messages.append({"role": "tool", "tool_call_id": tc.id, "content": output})
```

The Part 11 redefinition becomes:

```python
log_tool(thread_id, tc.id, name, args, output)
if len(output) <= 600:
    preview = output
else:
    preview = (
        output[:600] +
        f" ...[+{len(output)-600} bytes. "
        f"full output: fetch_tool_output(tool_call_id='{tc.id}')]"
    )
messages.append({"role": "tool", "tool_call_id": tc.id, "content": preview})
```

Two changes:

- `log_tool(...)` — full output → OAMP memory tagged with the `tool_call_id`.
- `preview` — what actually goes into the next LLM call. Compact, with a recovery hint.

## How the model uses it

1. Turn N: model calls `run_sql("SELECT * FROM cargo_items")`. Output is 12 KB.
2. The harness logs the full 12 KB to OAMP and inlines a 600-byte preview ending in `...[+11400 bytes. full output: fetch_tool_output(tool_call_id='call_X7Y')]`.
3. Model reads the preview. If 600 bytes is enough to answer (e.g., the user just wanted the count), it answers and the loop exits.
4. If 600 bytes isn't enough, the model emits a tool call: `fetch_tool_output(tool_call_id="call_X7Y")`. The harness retrieves the full 12 KB from OAMP and returns it. The model answers with the complete data.

Crucially, this decision is **the model's** — not a heuristic. Bandwidth follows attention.

## Key Takeaways — Part 11

- **Inlining every tool output blows the window.** A 50-row `run_sql`, a multi-KB skill body, or a long `exec_js` log can each consume more context than the rest of the turn combined.
- **Offload + truncation marker is the pattern.** Full output → OAMP memory tagged with `tool_call_id`. Compact preview → message list. The marker tells the model where the rest is.
- **The agent decides what to retrieve.** Most truncated outputs are never refetched — the model only pulls full bytes when its preview isn't enough.

## Troubleshooting

**`fetch_tool_output` returns "no tool call with id …"** — the `tool_call_id` doesn't match any OAMP memory. Either the offload write failed, or the tool_call_id was mangled. Check `memory_client._store.list(...)` directly with the same filter.

**Truncation marker shows but model never calls fetch_tool_output** — that's usually fine; the model decided the preview was enough. If you suspect it's misreading the marker, lower the truncation threshold (currently 600 bytes) or change the marker text to be more explicit.

**Full outputs accumulate in OAMP and the table grows** — yes, that's by design. In production, prune `kind=tool_output` memories older than N days from OAMP, or scope them to a specific `thread_id` and delete on thread close.
