# Part 5: Web Access with Tavily

## Why Agents Need Web Access

An agent's parametric knowledge (what the LLM was trained on) has a cutoff date and gaps. For tasks involving current events, live data, or domain knowledge not in the knowledge base, the agent needs to reach the web.

Tavily is an AI-optimised search API. Unlike general search APIs that return raw HTML, Tavily returns cleaned, summarised content designed for LLM consumption. This means:

- Less noise in the context window
- Lower token cost per search result
- Content that is already structured for reading, not for web rendering

## Tavily API Key

Your `TAVILY_API_KEY` is pre-configured as a Codespace environment variable — no manual setup required. The notebook loads it automatically via `os.environ.get("TAVILY_API_KEY")`.

## TODO 14: Register `search_tavily` as a Tool

The `@toolbox.register_tool(augment=True)` decorator does two things:

1. Makes the function callable by the agent as a tool
2. With `augment=True`, embeds the function's docstring and stores it in `TOOLBOX_MEMORY` — so the agent can find this tool via semantic search

**The docstring matters.** It is what the agent reads to decide whether to call this tool. Write it as if you are explaining to the agent when and why to use it.

**Important:** The function **must** be named `search_tavily` — the agent harness references this name to trigger a context refresh after web searches.

**Complete solution:**

```python
from tavily import TavilyClient
from datetime import datetime

tavily_client = TavilyClient(api_key=tavily_api_key)

@toolbox.register_tool(augment=True)
def search_tavily(query: str, max_results: int = 5):
    """
    Use this function to search the web and store the results in the knowledge base.
    """
    response = tavily_client.search(query=query, max_results=max_results)
    results = response.get("results", [])

    for result in results:
        text = f"Title: {result.get('title', '')}\nContent: {result.get('content', '')}\nURL: {result.get('url', '')}"
        metadata = {
            "title": result.get("title", ""),
            "url": result.get("url", ""),
            "score": result.get("score", 0),
            "source_type": "tavily_search",
            "query": query,
            "timestamp": datetime.now().isoformat()
        }
        memory_manager.write_knowledge_base(text, metadata)

    return results
```

**Why it writes to the knowledge base:** Unlike a simple search that returns and forgets, this tool persists every result into `SEMANTIC_MEMORY`. On future turns, the agent can retrieve these results via `read_knowledge_base` without searching again — the web content becomes part of the agent's long-term memory.

## How Tool Registration Works

After registering the tool, the next cell demonstrates semantic tool retrieval:

```python
retrieved_tools = memory_manager.read_toolbox("Search the internet")
```

This query searches `TOOLBOX_MEMORY` semantically and returns tools whose descriptions are relevant to the query. The agent uses this same mechanism on each turn to decide which tools to include in its context — instead of being given all tools every time.

This is the **toolbox pattern**: register tools into a vector store, retrieve relevant tools per query. At scale (hundreds of tools), this prevents the tool list from consuming large portions of the context budget.

## Understanding `augment=True`

The `augment` parameter controls whether the tool's description is stored in memory for semantic retrieval. Set it to `True` for tools that should be discoverable by the agent based on task relevance. Set it to `False` for tools that should always be available regardless of the current task (like a `get_time` utility).

## Troubleshooting

**`AuthenticationError` from Tavily** — Your API key is incorrect or not set. Verify the `TAVILY_API_KEY` environment variable is configured in your Codespace repo settings.

**`AssertionError: TAVILY_API_KEY not set`** — The environment variable is missing. Check your Codespace repo settings and rebuild if needed.

**Empty results** — Tavily free tier has rate limits. Wait a moment and retry.
