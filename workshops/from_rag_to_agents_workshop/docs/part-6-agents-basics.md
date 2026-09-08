# Part 6: AI Agents — Basics & Tools [Agent Foundation]

## What You Are Building

In this part you move from a single RAG call to an agentic system. The key shift: instead of you choosing the retrieval strategy, the agent decides which tools to call and how to combine results.

1. Install the OpenAI Agents SDK
2. Create a baseline agent (no tools)
3. Expose Oracle retrieval as a callable tool
4. Add a second tool for past research conversations
5. Strengthen agent instructions for tool routing

## Install Agent Runtime

```python
%pip install -Uq --no-cache-dir openai openai-agents
```

This installs the `agents` package which provides `Agent`, `Runner`, `function_tool`, and orchestration primitives.

## Baseline Agent (No Tools)

Start simple — define a research assistant and run a direct query:

```python
from agents import Agent, Runner

research_paper_assistant = Agent(
    name="Research Paper Assistant",
    model=OPENAI_MODEL,
    instructions="You are a Research Paper Assistant...",
)
result = await Runner.run(research_paper_assistant, input="Summarize recent research on optimization")
```

**Why start without tools?** This baseline demonstrates what the agent can do from parametric knowledge alone. The contrast with the tool-equipped agent in the next step makes the value of retrieval-augmented tools visible.

---

## TODO 5: Implement `get_research_papers` Tool

Wrap the SQL retrieval functions from Part 4 in an `@function_tool` decorator so the agent can call them autonomously.

**Requirements:**

1. Accept `user_query`, `retrieval_mode` (default "hybrid"), and `top_k` (default 5)
2. Route to the correct retrieval function based on mode
3. Format results as a readable string with numbered citations
4. Return the formatted string

**Why `@function_tool`?** This decorator registers the function with the Agents SDK so the model can call it by name. The SDK handles the JSON schema generation from the function's type hints and docstring — the model sees the tool description and parameter types automatically.

**The docstring matters.** It is what the agent reads to decide whether to call this tool. Write it as if you are explaining to the agent when and why to use it.

**Complete solution:**

```python
from agents.tool import function_tool

@function_tool
def get_research_papers(user_query: str, retrieval_mode: str = "hybrid", top_k: int = 5) -> str:
    """Retrieves academic research papers relevant to the user's query."""
    if retrieval_mode == "keyword":
        rows, columns = keyword_search_research_papers(conn, user_query)
    elif retrieval_mode == "vector":
        rows, columns = vector_search_research_papers(conn, embedding_model, user_query, top_k)
    elif retrieval_mode == "graph":
        rows, columns = graph_search_research_papers(conn, embedding_model, user_query, top_k=top_k)
    else:
        rows, columns, _ = hybrid_search_research_papers_pre_filter(
            conn=conn, embedding_model=embedding_model,
            search_phrase=user_query, top_k=top_k, show_explain=False
        )

    if not rows:
        return f"No papers found for '{user_query}'."

    formatted = [f"{len(rows)} papers retrieved for: '{user_query}'\n"]
    for i, row in enumerate(rows):
        row_data = dict(zip(columns, row))
        title = row_data.get("TITLE", "Untitled")
        abstract = row_data.get("ABSTRACT", "No abstract.")
        score = (row_data.get("GRAPH_SCORE") or row_data.get("SIMILARITY_SCORE")
                 or row_data.get("RELEVANCE_SCORE") or "N/A")
        formatted.append(f"[{i+1}] {title}\nAbstract: {abstract}\nScore: {score}\n")
    return "\n".join(formatted)
```

**Key concept:** The tool uses `conn` and `embedding_model` from the outer scope (closures). This is intentional — the agent should not manage database connections. The tool encapsulates all retrieval complexity behind a simple string-in, string-out interface.

## Second Tool: Past Research Conversations

The `get_past_research_conversations` tool follows the same `@function_tool` pattern but searches for prior analyses rather than raw papers. This gives the agent continuity — it can reference what it said in previous sessions.

## Strengthening Agent Instructions

Tool availability alone is not enough. Clear instructions make routing explicit:

- When to call paper retrieval
- When to call conversation retrieval
- When to combine both

**This is a key lesson: agent instructions are the control plane for tool selection.** A model with the right tools but vague instructions will under-use them. A model with clear instructions will consistently route queries to the right tool.

## Troubleshooting

**"ImportError: cannot import name 'Agent'"** — Restart the kernel after installing `openai-agents`.

**Agent doesn't call tools** — Check that tools are attached: `agent.tools.append(get_research_papers)`. Also verify the agent instructions explicitly describe when to use each tool.

**Tool returns empty results** — The same debugging applies as Part 4. Test the retrieval function directly before blaming the agent.
