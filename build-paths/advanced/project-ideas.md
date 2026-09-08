# Advanced — project ideas

Three projects, each composed from the **`build-paths/skills/`** building-block library. The point of this tier isn't "write the most complex Oracle code" — the original 8-idea version did that, and the volume of unique boilerplate per project was the bottleneck. This version is the inverse: each project's skill leans on three reusable building blocks, then writes ~500-700 LOC of *application logic only*.

The skills:

| Skill | Owns | Invoked when |
| --- | --- | --- |
| `skills/oracle-aidb-docker-setup` | Oracle 26ai Free in Docker (compose, password, healthcheck, smoke connect) | First step of every project. |
| `skills/langchain-oracledb-helper` | `OracleVS` wiring (multi-collection, monkeypatch, `OracleChatHistory`, embedder dim guard) | After the DB is up, before any app code. |
| `skills/oracle-mcp-server-helper` | `oracle-database-mcp-server` over stdio + LangChain tool conversion (`load_mcp_tools`) | When the agent needs live SQL / schema introspection. |

The advanced `SKILL.md` orchestrates: it picks **collections, embedder, allowed MCP tools, sql_mode**, hands those to the building blocks, then writes the per-project app code (chain, agent loop, UI, ingestion).

The skill maps free-text pitches to the closest of the three. If nothing maps, default to **idea 1 (NL2SQL + doc-RAG analyst)** — it's the most production-feeling demo and exercises all three skills equally.

---

## Universal stack

| Layer | Choice |
| --- | --- |
| DB | Oracle 26ai Free (via `skills/oracle-aidb-docker-setup`) |
| Vector store | `OracleVS` with `InDBEmbeddings` (registered ONNX `MY_MINILM_V1`, 384 dim) |
| LLM | OCI GenAI `xai.grok-4` (bearer-token API key, OpenAI-compat endpoint at `us-phoenix-1`) |
| Tools | `oracle-database-mcp-server` over stdio (`list_tables`, `describe_table`, `run_sql`, `vector_search`) |
| Agent | LangChain tool-calling agent over OAMP-backed memory |
| UI | Open WebUI (`:3000`) → FastAPI adapter (`:8000`) |
| Conversational + per-user durable memory | **OAMP** (`oracleagentmemory`) — threads, auto-extraction, context cards, schema-managed. See `shared/references/oamp.md`. Idea 3 is the single exception (DDL audit shape, not retrieved memory). |
| **Forbidden** | Redis, Postgres, SQLite, Chroma, FAISS, Qdrant, Pinecone — Oracle is the *only* state store. `verify.py` greps for forbidden imports and fails the build if any sneak in. |

---

## 1. NL2SQL + doc-RAG hybrid analyst (production-feeling)

**Pitch.** A real-world data analyst that can both query your live Oracle schema in natural language **and** RAG over your business documentation (runbooks, glossary, policies, decision docs). Knows when to do which. Multi-user from day one — each analyst's preferences and durable facts are scoped per user via OAMP.

**Why this is advanced.** Tier 2's NL2SQL agent was tools-over-SQL. Tier 2's hybrid retrieval was vector+SQL across two collections. This project **fuses** both *and* adds a routing layer — the agent first decides "is this a data question or a knowledge question?" then picks the right tool family. With **OAMP** managing the conversational + per-user durable memory layer (threads, auto-extracted facts, context cards), the agent can stitch turn N's data answer into turn N+1's documentation lookup ("explain that anomaly using our runbooks") *and* recall preferences across sessions ("Alice always wants the SQL behind the answer").

**Memory layer.**

| Memory | Primitive | What's in it |
| --- | --- | --- |
| Conversational + per-user durable | **OAMP** | Thread per `(user, agent)`, message log, auto-extracted facts ("Alice leads EU growth"), prompt-ready context card. Multi-user out of the box. |
| Glossary corpus (fixed) | `OracleVS` `GLOSSARY` | "churn_score = ...", "MRR = ..." — not user-scoped. |
| Runbooks corpus (fixed) | `OracleVS` `RUNBOOKS` | Ops procedures, incident docs. |
| Decisions corpus (fixed) | `OracleVS` `DECISIONS` | ADRs, architecture decisions. |

**Skills composition.**

```
skills/oracle-aidb-docker-setup     → DB up
skills/langchain-oracledb-helper    → store.py with collections=[GLOSSARY, RUNBOOKS, DECISIONS]
                                       (CONVERSATIONS dropped — OAMP owns conversational state)
skills/oracle-mcp-server-helper     → mcp_client.py exposing list_tables/describe_table/run_sql/vector_search
                                       (sql_mode=read_only, allowed_tools=all)

advanced writes:
  src/<pkg>/memory.py     # thin wrapper around shared/snippets/oamp_helpers
                          #   → get_thread(user_id, agent_id) → OAMP thread
                          # routes per-user conversation + durable memory through OAMP
  src/<pkg>/router.py     # classifies turn → "data" | "docs" | "both"
  src/<pkg>/agent.py      # the Grok-4 tool-calling loop
  src/<pkg>/ingest.py     # walks user's `data/` dir, embeds into the right collection
  src/<pkg>/adapter.py    # FastAPI /v1/chat/completions
```

**LOC.** ~550 of project-specific code (down from ~700 — OAMP eats the chat-history wiring + the memory adapter the original idea hand-rolled).

**Demo flow.**
1. Run `python -m <pkg>.ingest data/runbooks/ --collection RUNBOOKS` — chunks + in-DB embeddings.
2. Open Open WebUI.
3. Ask "what was Q3 revenue in EU?" → agent picks SQL family, runs `SELECT SUM(...)`, answers with the SQL it ran.
4. Ask "what does churn_score mean?" → agent picks vector family, retrieves from `GLOSSARY`, cites doc title.
5. **Auto-extraction.** Mid-conversation: "by the way, I lead the EU growth team." → no explicit `save_memory` call; OAMP extracts that into per-user durable memory automatically (defaults: every 2 turns over a 4-message window).
6. **Cross-thread recall.** Open a fresh thread the next day, ask "what should I prioritize?" → context card already includes "Alice leads EU growth," answer is scoped accordingly.
7. Ask "explain why our churn spiked last quarter using our runbooks" → router fires both: SQL for the spike data, vector for the runbook context.
8. Kill the app, restart, ask "summarize the conversation so far" → `client.get_thread(saved_id)` recovers the full thread + context card on a fresh process.

**Distinct value.** Closest thing to "what would I actually ship at work" in the catalog. Demonstrates the full Oracle pitch — vector + relational + OAMP-managed agent memory in one DB, joinable.

---

## 2. Self-improving research agent (autonomous, AutoGPT-shape)

**Pitch.** Hand the agent a long-running research task ("survey the state of in-DB ML for the next quarterly roadmap"). It plans steps, calls MCP tools, fetches external pages via a built-in `web_fetch` tool, summarizes findings, and **writes its own past tool calls and outcomes back into a vector store**. Future runs retrieve from that history before deciding what to try next. Over time it learns what works for *your* problem domain.

**Why this is advanced.** This project **uses Oracle as agent memory**, not just as RAG storage. Three memory types live in the DB, each on the right primitive:

| Memory | Primitive | What's in it |
| --- | --- | --- |
| **Toolbox** | `TOOL_REGISTRY` (relational SQL table) | List of tools the agent has discovered + success/fail counters. Relational counters, not retrieval — wrong shape for OAMP, wrong shape for OracleVS. |
| **Execution log** | `TOOL_RUNS` (`OracleVS`) | Embedded record of each `(tool, args, result, success_score)` tuple. Searchable by "what did I try last time I had a question like this?" Structured execution telemetry, not a conversation — keep in OracleVS. |
| **Session summary + per-task running context** | **OAMP** | Thread per `(user, agent)`, message log, auto-extraction, context card. Replaces the hand-rolled `SESSION_SUMMARIES` collection — OAMP's `thread.get_context_card()` plus the rolling summary IS the summary store. |

**Skills composition.**

```
skills/oracle-aidb-docker-setup     → DB up
skills/langchain-oracledb-helper    → store.py with collections=[TOOL_RUNS, FINDINGS]
                                       (SESSION_SUMMARIES dropped — OAMP owns session summary storage now)
                                       (CONVERSATIONS dropped — OAMP owns conversational state)
skills/oracle-mcp-server-helper     → mcp_client.py (read_only — agent reads its own logs via SQL too)

advanced writes:
  src/<pkg>/memory/toolbox.py     # SELECT/INSERT into TOOL_REGISTRY (unchanged — relational)
  src/<pkg>/memory/log.py         # append + retrieve TOOL_RUNS rows (unchanged — OracleVS)
  src/<pkg>/memory/summary.py     # OAMP-backed: thread + context_card; thin wrapper around oamp_helpers
  src/<pkg>/tools/web_fetch.py    # plus any task-specific tools
  src/<pkg>/agent.py              # planner-executor loop with OAMP context-card pull before each step
  src/<pkg>/adapter.py            # FastAPI; supports streaming long-running tasks
```

**LOC.** ~950 of project-specific code (down from ~1100 — OAMP eats the hand-rolled SESSION_SUMMARIES collection plus the cold→warm resume scaffolding).

**Demo flow.**
1. First run: hand it "research the current state of vector indexes in Oracle 26ai Free; produce a 1-page brief."
2. Watch it call `vector_search` (over its initially-empty `TOOL_RUNS`), then `web_fetch`, then `run_sql` against `SYSTEM` views, then summarize.
3. Each tool call is appended to `TOOL_RUNS` with an embedding of the (tool_name + args_json + truncated_result + score).
4. At session end, the OAMP thread's rolling summary already captures the gist (no separate summary write needed); per-user durable facts (e.g. "user wants briefs in markdown") are auto-extracted.
5. Second run, different task: "research IVF vs HNSW tradeoffs in Oracle." The agent's first step is now `vector_search` over `TOOL_RUNS` — finds its previous `run_sql` against `V$SYSAUX_OCCUPANTS`, decides not to repeat that path, picks a fresh angle. The OAMP context card layers in cross-task user preferences.
6. **Cold→warm proof.** Kill mid-task, restart on a fresh process. `OAMP.get_thread(saved_thread_id)` brings the context card back — the hand-rolled cold→warm proof from v3 is now an OAMP feature, not project code.

**Callout — OAMP threads as the resume mechanism.** The cold→warm proof at this tier used to require ~150 LOC of session-state plumbing in `memory/summary.py` plus a workflow tracker. OAMP's `get_thread(thread_id)` does the entire thing for free: kill the agent mid-task, reopen on a fresh process, the context card returns the prior conversation + extracted memories + rolling summary intact. We delete the hand-rolled cold→warm code; the demo gets stronger.

**Distinct value.** This is the closest to "AutoGPT shape" but **constrained to Oracle**. No vector DB sidecar, no Redis state store. Demonstrates Oracle as long-term agent memory across the right three primitives — relational counters, vector telemetry, and OAMP-managed conversation state.

---

## 3. Conversational schema designer (end-to-end builder)

**Pitch.** Talk to the agent about your domain ("I'm building a small SaaS that tracks pottery commissions and customer relationships"). It designs the schema, runs DDL via MCP, generates JSON Duality views over the resulting tables, ingests sample data you describe, and lets you query the result in NL — all in one conversation.

**Why this is advanced.** This is the only project in the catalog where the agent has **`sql_mode=read_write`**. Demonstrates:

- **DDL via MCP** with safety rails (the agent has to pass each DDL through a confirm step before executing, surfaced in the UI).
- **JSON Duality** — once tables exist, the agent generates `JSON RELATIONAL DUALITY VIEW` definitions with `WITH INSERT UPDATE DELETE` annotations so the same data can be written via JSON document API and read via SQL.
- **Schema-aware generation** — the agent re-reads its own work via `describe_schema` before each new step. No "what was that table called again?" bugs.

**Skills composition.**

```
skills/oracle-aidb-docker-setup     → DB up (with the schema designer's user_dir mounted for migrations)
skills/langchain-oracledb-helper    → store.py with collections=[DESIGN_HISTORY, CONVERSATIONS]
                                       (design_history captures every (DDL, rationale) pair the agent emits)
skills/oracle-mcp-server-helper     → mcp_client.py with sql_mode="read_write"
                                       allowed_tools=[list_tables, describe_table, describe_schema, run_sql]
                                       — explicit user confirmation captured at scaffold time, surfaced in README

advanced writes:
  src/<pkg>/migrations.py     # tracks every DDL the agent runs in a `migrations` table; can replay
  src/<pkg>/duality.py        # JSON Duality view generator + validator
  src/<pkg>/seeder.py         # NL → INSERT statements via grok-4
  src/<pkg>/agent.py          # the conversation loop with confirmation gating
  src/<pkg>/adapter.py        # FastAPI; emits structured events for confirmation prompts in Open WebUI
```

**LOC.** ~900 of project-specific code. Confirmation gating + DDL tracking + Duality view generation is the bulk.

**Demo flow.**
1. "I want to track pottery commissions. Customers commission pieces, each piece has stages (sketch → throw → glaze → fire → ship), and customers can have multiple addresses."
2. Agent proposes schema (3-4 tables: customers, addresses, commissions, stages). User says "looks good."
3. Agent runs DDL via MCP — each statement gates on UI confirm.
4. Agent generates Duality views: `commission_with_stages` (commission joined with all stages), `customer_with_addresses_and_commissions`.
5. User says "seed it with 5 fake customers, each with 1-3 commissions." Agent generates `INSERT` statements, runs them.
6. User: "show me which customer has the most active commissions." Agent runs `SELECT` against the data it just inserted. Returns answer.
7. User: "now give me JSON for customer 1's profile." Agent reads via the Duality view, returns the document.
8. End of session, agent writes its `migrations.py` tracker to disk so the user can replay this whole schema build on a fresh DB.

**Distinct value.** "Build a working database from a conversation." The single most demo-able idea in the catalog — shows the agent **using** Oracle's full surface (DDL, vector, Duality, query) without rolling its own anything.

**Safety note.** This project enables `read_write` MCP mode. The skill **requires** an explicit `y` from the user during interview (not the default-to-y form), and the README has a top-of-file warning. A `--dry-run` flag in `agent.py` lets the user see all the DDL the agent would run without executing.

**Memory note.** Memory at this idea is a structured DDL audit (`DESIGN_HISTORY`) — not conversational/per-user retrieval, so OAMP isn't a fit. The conversational layer (`OracleChatHistory`) wraps the audit but isn't the demo; the demo is the DDL trail and replay.

---

## What the skill won't scaffold at this tier

- **Multi-tenant auth.** Out of scope. The advanced agents assume single-user.
- **Production deployment guide.** No nginx, no TLS, no auth proxy. The user can wrap Open WebUI + the adapter in their own infra; the skill won't.
- **Anything that needs a non-Oracle store.** `verify.py` greps `src/` for `import (redis|psycopg|psycopg2|sqlite3|chromadb|qdrant_client|pinecone|faiss)` and fails if any are present.
- **Bring-your-own LLM at this tier.** OCI GenAI Grok 4 only. Ollama as fallback was removed when this tier moved to "advanced" — running an autonomous agent over a local 8B model is a recipe for tool-call infinite loops.

---

## What you get (sanity check)

By the time `verify.py` reports OK on an advanced project:

- Healthy Oracle 26ai Free container.
- Registered `MY_MINILM_V1` ONNX model.
- All collections bootstrapped (the project's specific list).
- `oracle-database-mcp-server` process attached, tools listed.
- FastAPI adapter on `:8000`, Open WebUI on `:3000`.
- For idea 2: empty `TOOL_RUNS` + `SESSION_SUMMARIES` ready to be populated.
- For idea 3: empty schema, agent confirmed `read_write` mode, dry-run mode tested.
- A README with the OCI cost note + the skills-library composition diagram + the "which features does this project use" matrix.
- A short notebook (3-5 cells) demoing the project end-to-end without the UI — useful for explainer videos.

That's the deliverable. The user should be able to record a 2-3 minute demo of the agent doing real-feeling work.
