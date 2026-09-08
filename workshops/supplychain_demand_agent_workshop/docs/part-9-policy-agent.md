# Part 9 — `policy_agent` specialist

## What this specialist does

The `policy_agent` answers two distinct questions:

1. **"What's the standing buy-volume policy?"** — pulls the policy memo
   from `OracleVS`.
2. **"What does this specific planner prefer?"** — pulls user-scoped
   memories from `AsyncOracleStore`, keyed by `user_id`.

Two questions, two tools. One agent.

## Tool 1 — `get_planner_policy` (sync, no args)

```python
@tool
def get_planner_policy() -> str:
    """Fetch the standing planner-prefs buy-volume policy from OracleVS."""
    docs = oracle_vs.similarity_search("planner buy volume policy", k=1)
    return docs[0].page_content if docs else "No policy on file."
```

It's a targeted similarity search by intent ("policy"), with `k=1`.
The seed step wrote exactly one policy memo into `OracleVS` with
metadata `{"type": "policy", "name": "planner_buy_volume"}`, so this
always returns that single document.

## Tool 2 — `get_user_memory` (async, takes `user_id`)

```python
@tool
async def get_user_memory(user_id: str) -> str:
    """Look up long-term saved preferences for a planner by their user_id."""
    items = await agent_store.asearch(
        ("users", user_id, "memories"),
        query="preference",
        limit=3,
    )
    if not items:
        return f"No saved memories for user_id={user_id}."
    return "\n".join(f"- {it.value.get('note', '')}" for it in items)
```

Two things to notice:

1. **`async def`.** `AsyncOracleStore.asearch(...)` is awaitable.
   `create_agent` handles async tools transparently — you don't need a
   sync-async wrapper.
2. **`("users", user_id, "memories")`** — the namespace pattern.
   `user_id` is interpolated from the function argument, so each
   planner sees only their own memories.

## Routing `user_id` through the supervisor

How does the `policy_agent` know which `user_id` to look up? The
**user mentions it in the request**:

> _"I'm planner with user_id=priya. Pull demand intel and draft a buy
> recommendation that respects my preferences."_

The supervisor delegates to `policy_agent` and the specialist's LLM
parses `user_id=priya` out of the message before deciding to call
`get_user_memory(user_id="priya")`. We don't need a structured input
schema — the system prompt tells the agent that `user_id` arrives in
the supervisor's request.

## The system prompt

```python
policy_agent = create_agent(
    agent_model,
    tools=[get_planner_policy, get_user_memory],
    system_prompt=(
        "You are the policy and preference agent. Use `get_planner_policy` for the "
        "standing buy-volume policy, and `get_user_memory(user_id=...)` for the active "
        "planner's saved preferences (the user_id is mentioned in the supervisor's "
        "request). Return both verbatim — do not editorialise."
    ),
    name="policy_agent",
)
```

The `"Return both verbatim"` instruction is deliberate: we don't want
this specialist to _interpret_ the policy or the user preference. That
interpretation is the supervisor's job (Part 10). Specialists report;
the supervisor decides.

## What you'll build in TODO 8

Both tools and the `create_agent` call. The hard-stop checkpoint:

1. Calls `get_planner_policy.invoke({})` and asserts the result
   contains "policy" or "500" (the policy threshold).
2. Calls `get_user_memory.ainvoke({"user_id": "priya"})` and asserts
   the note contains "conservative" (Priya's preference).

If either fails, you've either pointed at the wrong table/namespace or
your implementation isn't returning what the tool's docstring promises.

## Solution

Drop this into the TODO 8 cell, replacing both `raise NotImplementedError`
bodies and the `policy_agent = None` line:

```python
@tool
def get_planner_policy() -> str:
    """Fetch the standing planner-prefs buy-volume policy from OracleVS."""
    docs = oracle_vs.similarity_search("planner buy volume policy", k=1)
    return docs[0].page_content if docs else "No policy on file."


@tool
async def get_user_memory(user_id: str) -> str:
    """Look up long-term saved preferences for a planner by their user_id."""
    items = await agent_store.asearch(
        ("users", user_id, "memories"),
        query="preference",
        limit=3,
    )
    if not items:
        return f"No saved memories for user_id={user_id}."
    return "\n".join(f"- {it.value.get('note', '')}" for it in items)


policy_agent = create_agent(
    agent_model,
    tools=[get_planner_policy, get_user_memory],
    system_prompt=(
        "You are the policy and preference agent. Use `get_planner_policy` for the "
        "standing buy-volume policy, and `get_user_memory(user_id=...)` for the active "
        "planner's saved preferences (the user_id is mentioned in the supervisor's "
        "request). Return both verbatim — do not editorialise."
    ),
    name="policy_agent",
)
print(f"policy_agent compiled on {LLM_PROVIDER}/{LLM_MODEL}")
```

## Next

→ **[Part 10 — Supervisor](part-10-supervisor.md)** — tie both specialists together with `langgraph_supervisor`.
