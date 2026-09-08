# Part 8 — `demand_analyst` specialist

## What a "specialist" is

In a multi-agent system, a **specialist** is a focused agent with a
small toolset and a tight job description. It doesn't try to do
everything — it does one thing well, returns a summary, and gets out
of the way.

The `demand_analyst` is our first specialist. Its one job: when asked
about a category or product line, search historical demand reports and
return a 3–5-sentence summary.

## One tool: `search_demand_reports`

A LangChain `@tool`-decorated function is the unit of capability an
agent can invoke. `search_demand_reports` wraps `OracleVS.similarity_search`:

```python
from langchain_core.tools import tool

@tool
def search_demand_reports(query: str) -> str:
    """Search historical product demand reports by semantic similarity."""
    docs = oracle_vs.similarity_search(query, k=5)
    if not docs:
        return "No matches."
    return "\n\n---\n\n".join(d.page_content for d in docs)
```

The agent calls this with a natural-language query, gets the top-5
reports back as one joined string, and reasons over them.

## Compiling the agent with `create_agent`

```python
from langchain.agents import create_agent

demand_analyst = create_agent(
    agent_model,
    tools=[search_demand_reports],
    system_prompt=(
        "You are a demand analyst. Given a category or product line, use "
        "`search_demand_reports` and return a concise 3-5 sentence summary "
        "covering volume direction, peak hours/days, and unique-visitor coverage."
    ),
    name="demand_analyst",
)
```

A few things to notice:

1. **`agent_model`** is provider-aware (`ChatOpenAI(model=LLM_MODEL,
**chat_model_kwargs())`). One agent, two providers, no code change.
2. **`tools=[search_demand_reports]`** — list of one. Small surface,
   less for the LLM to hallucinate.
3. **`name="demand_analyst"`** — _crucial_. The supervisor in Part 10
   uses this name when emitting a hand-off tool call. Without it the
   supervisor can't route to this agent.

The returned object is a compiled LangGraph state graph; it's
invocable as a sub-graph and exposes a `.name` attribute.

## Why this specialist doesn't synthesise

The `demand_analyst` does not write the final buy recommendation. It
just summarises demand. The supervisor (Part 10) writes the synthesis,
combining this specialist's output with the `policy_agent`'s output.

This separation matters: when you read a recommendation later, you can
trace each claim back to which specialist surfaced it.

## What you'll build in TODO 7

The two-cell implementation above. The hard-stop checkpoint asserts:

- `demand_analyst is not None` (you actually constructed it)
- `demand_analyst.name == "demand_analyst"` (you passed the `name` kwarg)

If `.name` is missing, the supervisor will silently fail to route
to this agent later.

## Solution

Drop this into the TODO 7 cell, replacing the `raise NotImplementedError`
in the tool body and the `demand_analyst = None` line:

```python
from langchain.agents import create_agent
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

@tool
def search_demand_reports(query: str) -> str:
    """Search historical product demand reports by semantic similarity."""
    docs = oracle_vs.similarity_search(query, k=5)
    if not docs:
        return "No matches."
    return "\n\n---\n\n".join(d.page_content for d in docs)


agent_model = ChatOpenAI(model=LLM_MODEL, **chat_model_kwargs())

demand_analyst = create_agent(
    agent_model,
    tools=[search_demand_reports],
    system_prompt=(
        "You are a demand analyst. Given a category or product line, use "
        "`search_demand_reports` and return a concise 3-5 sentence summary "
        "covering volume direction, peak hours/days, and unique-visitor coverage."
    ),
    name="demand_analyst",
)
print(f"demand_analyst compiled on {LLM_PROVIDER}/{LLM_MODEL}")
```

## Next

→ **[Part 9 — `policy_agent` specialist](part-9-policy-agent.md)** — the second specialist, with two tools and an async one.
