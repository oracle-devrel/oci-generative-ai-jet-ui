# examples/ — things you COPY, not code that runs

The distinction that keeps this repo navigable:

- **`scripts/`** = runnable code. Loaders, the sync job, maintenance tools.
  You execute these in place; you rarely edit them.
- **`examples/`** = starting points you **copy out** and make your own.
  Nothing in here runs as part of the system.

## Current starters

| Starter | Copy it to | What it gives you |
|---|---|---|
| [`obsidian-starter/`](obsidian-starter/) | anywhere on your machine (it becomes your vault / drop folder) | a minimal notes folder with the frontmatter conventions pre-documented — works with `scripts/obsidian.py` |
| [`example_loader.py`](example_loader.py) | `scripts/<your_source>.py` | a heavily-commented skeleton for writing a loader for ANY source — the whole contract is one table |
| [`langgraph_oamp.py`](langgraph_oamp.py) | your own agent project | a LangGraph agent with Oracle AI Agent Memory (OAMP) as its memory core — recall before the model runs, remember after; the same pattern fits the OpenAI Agents SDK or Claude Agent SDK |

## The loader contract (why a skeleton is enough)

Every source — YouTube, Notion, Drive, your vault — reduces to the same move:
map your source's fields onto `title`, `caption` (the text), `url` (a stable,
unique id for idempotency), `published_at`, and a platform id, insert into
`posts`, and add passage chunks for long text. Embeddings happen in-database
on insert. Search, the wiki, the agents, and MCP pick the new source up with
zero further wiring.
