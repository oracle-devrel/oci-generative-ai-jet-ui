# skills — reusable Oracle-AI building blocks

Three skills the build-paths system uses to scaffold projects without re-deriving the same boilerplate every time. Each one is invokable on its own (point any agent at the `SKILL.md`) and is also composed by the higher tiers — particularly the **advanced** path, which builds entire applications by chaining all three.

| Skill | What it owns | Cite when you need |
| --- | --- | --- |
| [`oracle-aidb-docker-setup`](./oracle-aidb-docker-setup/) | Oracle 26ai Free in Docker — compose file, password generation, `--wait` health gate, smoke connect. | A fresh local DB, on any machine with Docker. |
| [`langchain-oracledb-helper`](./langchain-oracledb-helper/) | `OracleVS` wiring — multi-collection wrapper, metadata-as-string monkeypatch, embedder dim assertion, `OracleChatHistory` (since `langchain-oracledb` doesn't ship one). | Any LangChain project using Oracle as its vector store. |
| [`oracle-mcp-server-helper`](./oracle-mcp-server-helper/) | `oracle-database-mcp-server` — install, connect over stdio, expose `list_tables` / `describe_table` / `run_sql` / `vector_search` as LangChain tools. | Any agent that needs to call SQL or schema introspection at inference time. |

## Composition pattern (how advanced uses these)

The advanced path's `SKILL.md` doesn't write a `docker-compose.yml` itself — it tells the agent to invoke `oracle-aidb-docker-setup`, which does. It doesn't write `store.py` — it invokes `langchain-oracledb-helper`. The advanced skill's job is **picking which collections, which models, which MCP tools**, then handing that spec to the building-block skills.

```
advanced/SKILL.md
    │
    ├── invokes ──→ skills/oracle-aidb-docker-setup    (DB up)
    │
    ├── invokes ──→ skills/langchain-oracledb-helper   (vector + history layer)
    │                       inputs: collections, embedder choice
    │
    ├── invokes ──→ skills/oracle-mcp-server-helper    (SQL / schema tool layer)
    │                       inputs: db connection string
    │
    └── writes app code that uses all three            (chain, UI, agent loop)
```

This is not just DRY for its own sake — it lets the advanced project be **smaller** (the agent only writes ~500-700 LOC of app-specific code, not 1500+). The skills handle the boring layers.

## Standalone use

Each skill works without the build-paths harness. From any directory:

> Read `<your-hub-checkout>/build-paths/skills/<skill-name>/SKILL.md` and follow it.

Replace `<your-hub-checkout>` with the absolute path to wherever you cloned the [oracle-ai-developer-hub](https://github.com/oracle-devrel/oracle-ai-developer-hub) repo on your machine.

The skill will ask its own inputs and run its own steps. Useful when you want to bolt the Oracle layer onto an existing app instead of scaffolding from zero.

## Why these three (and not more)

These three are the boundaries where most "I want to use Oracle for X" projects get stuck:

1. **Container setup** — Docker compose is fiddly the first time, fast forever after.
2. **`OracleVS` correctness** — the metadata monkeypatch + the missing `OracleChatHistory` class trip everyone up.
3. **MCP wiring** — connecting an LLM to live SQL via MCP is the modern shape but the docs are scattered.

A fourth skill (`oci-genai-helper` for Grok 4 wiring) is on the table but currently lives inline in each tier's `SKILL.md` — see `shared/references/oci-genai-openai.md`. Hoist it to `skills/` if it ends up duplicated three times.

## What these skills do NOT do

- They don't pick which **idea** you're building. That's `beginner/`, `intermediate/`, or `advanced/`.
- They don't write product code (the chat chain, the UI, the agent loop). That's the tier `SKILL.md`'s job.
- They don't manage your OCI account, secrets, or IAM. Bring your own `OCI_GENAI_API_KEY` (sk-... value from the OCI GenAI console).
