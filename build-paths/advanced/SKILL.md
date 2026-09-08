---
name: build-paths-advanced
description: Scaffold an agent system where Oracle AI DB is the *only* state store, composed from the build-paths/skills/ building-block library. Stack — langchain-oracledb + oracle-database-mcp-server + in-DB ONNX embeddings + OCI GenAI Grok 4 + Open WebUI. Three projects — production-feeling NL2SQL+RAG hybrid analyst, self-improving research agent, conversational schema designer. For users who want a real DB-as-only-store agent demo.
inputs:
  - target_dir: where to scaffold (default = current working directory; ask if it isn't empty)
  - topic: optional; one of advanced/project-ideas.md, or a free-text pitch within the constraint
---

The user picked the **advanced** path. Two non-negotiable rules at this tier:

1. **Oracle AI DB is the only state store.** No Redis, no Postgres, no SQLite, no Chroma/FAISS/Qdrant/Pinecone, no JSON or pickle on disk for runtime state. `verify.py` greps `src/` for forbidden imports and fails the build.
2. **You compose, you don't write boilerplate.** The Oracle layer comes from `skills/oracle-aidb-docker-setup`, `skills/langchain-oracledb-helper`, `skills/oracle-mcp-server-helper`. Your job is to **invoke those, then write the application logic** (the agent loop, the memory adapters, the tools, the adapter, the notebook). ~500-700 LOC of project code per idea — not 1500.

## Step 0 — Read these references first

- `skills/README.md` — the composition pattern.
- `skills/oracle-aidb-docker-setup/SKILL.md`
- `skills/langchain-oracledb-helper/SKILL.md`
- `skills/oracle-mcp-server-helper/SKILL.md`
- `shared/references/oamp.md` — load-bearing for the conversational + per-user durable memory layer (ideas 1 + 2).
- All of `shared/references/` — yes all of them. The advanced tier can touch every feature.
- `advanced/project-ideas.md`.

## Step 1 — Interview

Run `shared/interview.md` plus the advanced-only questions.

- **Q3 (DB target)** — local Docker default.
- **Q4 (Inference)** — *not optional*. **OCI GenAI** for chat (`xai.grok-4` via the OpenAI-compat bearer-token endpoint at `us-phoenix-1`; `OCI_GENAI_API_KEY` only — no `~/.oci/config` needed). **In-DB ONNX** for embeddings (`MY_MINILM_V1`, 384 dim) registered via `onnx2oracle` CLI.
- **Q5 (Topic)** — one of three from `advanced/project-ideas.md`. Map free-text pitches; default to idea 1 (NL2SQL + doc-RAG hybrid analyst).
- **Q6 (Notebook)** — yes, **mandatory**. Reject "no" — advanced is where notebook payoff lives.
- **Q7 (advanced-only) — sql_mode for MCP?** — `read_only` (default; ideas 1 + 2). **Idea 3 (conversational schema designer) requires `read_write`** and an explicit confirmation captured in writing — surface in the README as a callout.
- **Q8 (advanced-only) — Demo focus?** "Polished UI demo" / "Notebook deep-dive" / "Both" — affects how much Open WebUI vs notebook narrative the skill produces.

Print confirmation block. Wait for `y`.

## Step 2 — Resolve choices

| Variable | Source |
| --- | --- |
| `project_slug` | derived from chosen idea |
| `package_slug` | snake_case |
| `embedder` | `in-db-onnx` |
| `embedding_dim` | 384 |
| `onnx_model_local_id` | `sentence-transformers/all-MiniLM-L6-v2` |
| `onnx_model_db_name` | `MY_MINILM_V1` |
| `llm_model` | `grok-4` (or fallback) |
| `collections` | per-idea (see below) |
| `mcp_sql_mode` | per-idea: 1 = `read_only`, 2 = `read_only`, 3 = `read_write` (with explicit y) |
| `mcp_allowed_tools` | per-idea (see below) |
| `forbidden_imports` | hardcoded — `verify.py` greps for these |
| `notebook_focus` | from Q8 |

Per-idea collections + tools:

| Idea | OracleVS collections | OAMP? | MCP allowed_tools |
| --- | --- | --- | --- |
| 1 (hybrid analyst) | `[GLOSSARY, RUNBOOKS, DECISIONS]` (CONVERSATIONS dropped — OAMP owns it) | yes — conversational + per-user durable memory | `[list_tables, describe_table, run_sql, vector_search]` |
| 2 (self-improving research agent) | `[TOOL_RUNS, FINDINGS]` (SESSION_SUMMARIES + CONVERSATIONS dropped — OAMP owns both) | yes — session summary + per-user durable memory | `[list_tables, describe_table, run_sql, vector_search]` |
| 3 (conversational schema designer) | `[DESIGN_HISTORY, CONVERSATIONS]` | no — DDL audit shape; not retrieved memory | `[list_tables, describe_table, describe_schema, run_sql]` (read_write) |

## Step 3 — Scaffold

### 3a — Foundation via building-block skills

1. Refuse if `target_dir` is non-empty.
2. **Invoke `skills/oracle-aidb-docker-setup`.** Block until OK.
3. Append the **Open WebUI** service to the generated compose file (same as beginner / intermediate).
4. **Register the in-DB ONNX model via `onnx2oracle` CLI.** Same as intermediate Step 3a-4: `pip install onnx2oracle`, then `onnx2oracle load all-MiniLM-L6-v2 --name MY_MINILM_V1 --dsn "$DB_USER/$DB_PASSWORD@$DB_DSN" --force`. Smoke with `SELECT VECTOR_EMBEDDING(MY_MINILM_V1 USING 'test' AS data) FROM dual`. Required GRANTs (`CREATE MINING MODEL`, `EXECUTE ON SYS.DBMS_VECTOR`) are issued by `oracle-aidb-docker-setup` Step 6.
5. **Invoke `skills/langchain-oracledb-helper`.** Pass `embedder=in-db-onnx`, the per-idea collections, `has_chat_history=True` (idea 3 only — ideas 1+2 don't need OracleChatHistory; OAMP threads replace it). Block until OK.
6. **Invoke `skills/oracle-mcp-server-helper`.** Pass the per-idea `sql_mode` and `allowed_tools`. For idea 3, the helper will refuse to proceed silently — capture the explicit user `y` before invoking.
7. **Configure OAMP (ideas 1 + 2 only).** Copy `shared/snippets/oamp_helpers.py` into the project as `src/<package_slug>/oamp_helpers.py` and import `make_oamp_client(conn)` from there. Schema is auto-created (`schema_policy="create_if_necessary"`). Auto-extraction enables iff `OCI_GENAI_API_KEY` is set; otherwise the helper degrades to manual-add mode and the rest of OAMP still works. See `shared/references/oamp.md` for the full decision tree and the OAMP/OracleVS/OracleChatHistory/SQL split.

### 3b — Per-idea memory & app code

Write only the files specific to the chosen idea. Order: migrations → memory adapters → app code → adapter → notebook.

#### Idea 1 — Hybrid analyst

7. `migrations/100_seed_dummy.sql` — same fake schema as intermediate idea 1 (10 tables, ~50K rows via Faker).
8. `src/<package_slug>/router.py` — turn classifier. Two-step: small Grok call ("is this a data question, a knowledge question, or both?") → routes to SQL family / vector family / both. ~80 LOC.
9. `src/<package_slug>/ingest.py` — walks `data/` subdirs (`runbooks/`, `glossary/`, `decisions/`), embeds via in-DB `VECTOR_EMBEDDING`, inserts into the matching collection.
10. `src/<package_slug>/memory.py` — thin wrapper around `oamp_helpers`. Exposes `get_thread(user_id, agent_id="hybrid-analyst-v1")` which returns an OAMP thread (creates it if missing, otherwise reuses the existing thread for the user). Routes per-user conversation + durable memory through OAMP — replaces the OracleChatHistory wiring entirely. ~40 LOC.
11. `src/<package_slug>/agent.py` — tool-calling agent. Tools = MCP tools. The router's classification becomes a system-prompt hint that shapes which tool the agent picks first. Pulls `thread.get_context_card()` from `memory.py` and prepends it to the user turn before each LLM call.
12. `src/<package_slug>/adapter.py` — FastAPI `/v1/chat/completions`, streams agent events. Resolves `user_id` from the request (Open WebUI surfaces a stable id per browser session); routes through `memory.get_thread(user_id)`.

#### Idea 2 — Self-improving research agent

7. `migrations/100_tool_registry.sql` — relational `TOOL_REGISTRY (tool_name, signature, last_used, success_count, fail_count)`.
8. `src/<package_slug>/memory/toolbox.py` — `register_tool`, `mark_success`, `mark_fail`, `recommend_next` (SQL queries).
9. `src/<package_slug>/memory/log.py` — `append(tool, args, result, score)` writes to `TOOL_RUNS` (`OracleVS`) with embedding via `VECTOR_EMBEDDING`. `retrieve_similar(query)` uses `vector_search`.
10. `src/<package_slug>/memory/summary.py` — **OAMP-backed**. Thin wrapper around `oamp_helpers`: `get_or_create_thread(user_id, agent_id)` returns an OAMP thread; `record_turn(thread, role, content)` calls `add_turn(thread, role, content)` from `oamp_helpers` (one `add_messages()` per turn — batching breaks extraction, see `shared/references/oamp.md` V4-OAMP-1); `context_card(thread)` returns `thread.get_context_card()` for the planner to splice into the prompt. The hand-rolled `SESSION_SUMMARIES` collection is GONE — OAMP's rolling thread summary plus retrieved memories is the summary store now. Cold-start retrieval at session boot becomes `client.get_thread(saved_thread_id)` — recovers the same conversation across processes for free.
11. `src/<package_slug>/tools/web_fetch.py` — copy `shared/snippets/web_fetch_tool.py` verbatim. It's a `httpx.get` + `trafilatura.extract` BaseTool with a `(url, fallback_query)` signature so the agent can pivot to a corpus search when a URL 4xx/5xx or times out. The `corpus_search_fn` constructor arg is wired to `memory.log.retrieve_similar` (or any retriever you prefer) at scaffold time. Tool calls get logged via `memory.log.append`.
12. `src/<package_slug>/agent.py` — planner-executor loop. The skeleton (note: `memory.summary` calls now go through OAMP):
    ```python
    thread = memory.summary.get_or_create_thread(user_id, agent_id)
    memory.summary.record_turn(thread, "user", task)
    state = {"task": task, "context": thread.get_context_card(), "step": 0}
    while state["step"] < MAX_STEPS:
        relevant_runs = memory.log.retrieve_similar(state["task"])
        plan = grok.plan(state, relevant_runs)
        if plan.tool == "finish":
            break
        result = execute_tool(plan.tool, plan.args)
        memory.log.append(plan.tool, plan.args, result, score(result))
        memory.toolbox.mark_success_or_fail(plan.tool, ...)
        state = update(state, result)
    memory.summary.record_turn(thread, "assistant", state["final_answer"])
    # OAMP auto-extracts durable facts from the thread on the schedule defined
    # by memory_extraction_frequency; no explicit summary write needed.
    ```

    **Planner system-prompt rules (load-bearing — friction P1-9):**
    - Tool args MUST be a JSON object, never a list. Grok 4 will emit lists by default; correct this in the system prompt.
    - In `read_only` SQL mode, refuse `run_sql` calls whose statement starts with anything other than `SELECT` or `WITH ... SELECT` — the `RunSQLTool` already enforces this; the planner should also know.
    - Memory writes are AUTOMATIC at `finish`. The agent must not emit explicit `save_to_memory(...)` tool calls — the loop persists `summaries` and `tool_runs` for it.
    - `finish` substantively after **2-3 useful tool calls**. Don't wander; `MAX_STEPS=12` is a safety net, not a target.

    **Planner LLM call must allow enough tokens for `final_answer` (friction v2-F-v2-1).** The agent loop emits structured JSON containing the `final_answer` text alongside the tool plan. With `max_tokens=600` (the OCI default), Grok 4 can truncate mid-JSON at the boundary between the plan envelope and the answer — the JSON is unparseable and the loop crashes. Use `max_tokens=1500` minimum on the planner `chat_complete` call so `final_answer` (target 1000-1500 chars) fits with envelope overhead.

    Without these prompt rules the agent burns through `MAX_STEPS` and persists placeholder content into memory — observed in run #4.
13. `src/<package_slug>/adapter.py` — FastAPI `/v1/chat/completions` with streaming, exposes "task plan" + "tool calls" + "summary" as separate event types in the SSE stream so Open WebUI can render the agent's reasoning.

#### Idea 3 — Conversational schema designer

7. `migrations/100_design_history.sql` — `DESIGN_HISTORY (id, ddl, rationale, run_at, success)`.
8. `src/<package_slug>/migrations.py` — wraps every DDL the agent emits into a `DESIGN_HISTORY` row + executes it via `run_sql` MCP tool. Replay-capable: rerun `DESIGN_HISTORY` rows in order on a fresh DB.
9. `src/<package_slug>/duality.py` — JSON Duality view generator. Takes a list of base tables + relationships, emits `CREATE OR REPLACE JSON RELATIONAL DUALITY VIEW ... WITH INSERT UPDATE DELETE`. Validator checks the generated view loads without error before committing it to history.
10. `src/<package_slug>/seeder.py` — NL "seed it with 5 fake customers, each with 1-3 commissions" → grok generates `INSERT` statements → run via MCP. Captured in history.
11. `src/<package_slug>/agent.py` — conversation loop with **confirmation gating**: every DDL the agent wants to run is surfaced as a structured event in the SSE stream; the adapter holds the SQL until the UI POSTs back to `/confirm/<request_id>`. Open WebUI's tool-output rendering is enough — no custom frontend needed.
12. `src/<package_slug>/adapter.py` — FastAPI; supports the confirm endpoint plus standard `/v1/chat/completions`.

### 3c — Verify, notebook, README (all ideas)

13. `verify.py` — fill template:
    - `inference_enabled = True`.
    - Round-trip ONNX dim (== 384).
    - Smoke MCP tools list.
    - **Forbidden-imports grep:** `grep -RE 'import (redis|psycopg|psycopg2|sqlite3|chromadb|qdrant_client|pinecone|faiss)' src/`. Non-empty output = fail.
    - **OAMP cold→warm round-trip (ideas 1 + 2 only).** Construct an OAMP client, write a memory (`client.add_memory("verify-check fact", user_id="verify", agent_id="verify-bot")`), close the connection, reopen a new connection + new client, retrieve via `client.search("verify-check", user_id="verify")`, assert the fact comes back. This proves the DB-as-only-store invariant for OAMP.
    - Per-idea smoke:
      - 1: ingest the seed schema, ask "what was Q3 revenue?"; assert SQL ran.
      - 2: empty-task run + OAMP thread write + cold→warm thread recovery via `get_thread(saved_id)`.
      - 3: dry-run a `CREATE TABLE customers (...)` through the agent — assert it lands in `DESIGN_HISTORY` without executing.
14. `notebook.ipynb` — **mandatory at advanced; clean execution is a Bar B requirement, not optional**. The notebook is the demo payoff (the "what does this thing actually do?" artifact for an influencer demo).
    - `polished_ui` focus → 8 cells, last launches the adapter (and you open WebUI manually).
    - `deep_dive` focus → 12-15 cells per idea, walks every component (memory, MCP, agent loop, ONNX SQL).
    - `both` → 12-15 cells, last launches.
    Cells must execute clean via `jupyter nbconvert --to notebook --execute notebook.ipynb`. Save the executed copy alongside the source so reviewers can see the outputs without re-running.
15. `README.md` — the "Why Oracle" paragraph names: in-DB ONNX, vector + relational + JSON Duality + property graph (idea 1 references the agentic_rag-style 6-memory pattern; ideas 2 + 3 use specific subsets), MCP server. Include a **"Skills composition" diagram** (mermaid) showing the three skills feeding into the project. Include the "DB-as-only-store proof" callout pointing at the verify forbidden-imports grep.

## Step 4 — Verify

1. DB up (skill 1 ensured).
2. ONNX registered (step 3a-4).
3. `python -m pip install -e .`
4. `python verify.py`. Expect `verify: OK (db, vector, inference, mcp, memory, oamp, no_forbidden_imports)` (idea 3 reports `oamp: skipped — DDL-audit shape, not retrieved memory`).
5. Run the notebook clean.
6. Boot adapter, hit `/v1/models`, kill it.
7. On any failure, follow `shared/verify.md` recovery loop, max 3 retries.

### Resetting memory between dev runs (idea 2 specifically)

Running the agent twice in dev pollutes memory tables — by design. To reset between iterations:

```sql
TRUNCATE TABLE TOOL_RUNS;
TRUNCATE TABLE FINDINGS;
DELETE FROM TOOL_REGISTRY;  -- not TRUNCATE — IDENTITY column counter resets weird
COMMIT;
```

Plus reset OAMP-managed state (the OAMP client owns its own tables):

```python
# scripts/reset_oamp.py
from <package_slug>.oamp_helpers import make_oamp_client
from <package_slug>.store import get_connection
client = make_oamp_client(get_connection())
# Delete every thread + memory for the dev user/agent pair:
for t in client.list_threads(user_id="dev", agent_id="dev-bot"):
    client.delete_thread(t.thread_id)
# `recreate` schema_policy on construction is an alternative — drops and
# rebuilds OAMP tables. Faster than per-row delete; nukes everything.
```

Add a `scripts/reset_memory.py` that runs the SQL block + the OAMP block. The notebook's last cell can call it for a clean re-run.

## Step 5 — Polish for sharing

1. README placeholders filled.
2. `docs/` — placeholders for: demo GIF, screenshot of Open WebUI, mermaid skills-composition diagram.
3. Final report:
   ```
   Done.
     project at:    <target_dir>
     features used: in-DB ONNX, OracleVS multi-collection, OAMP (ideas 1+2) | OracleChatHistory (idea 3), oracle-database-mcp-server, <idea-specific>
     skills used:   oracle-aidb-docker-setup, langchain-oracledb-helper, oracle-mcp-server-helper
     run with:      cd <target_dir>
                    docker compose up -d
                    python -m <pkg>.adapter   # blocks; Open WebUI on :3000
     verify:        OK (no forbidden imports)
     notebook:      <target_dir>/notebook.ipynb (executed clean)
     proof:         no Redis/Postgres/SQLite/Chroma/etc — verified by grep.
     next:          record 2-3 min demo, fill "What I built", architecture diagram, push.
   ```

## Stop conditions

- User declines OCI GenAI (no tenancy / cost concern). Tell them this tier requires it.
- User declines the Oracle-as-only-store constraint. Suggest intermediate path instead.
- ONNX model registers but dim ≠ 384. Drop, surface error, stop.
- Idea 3 picked but user won't confirm `read_write` MCP. Default to read_only blocks idea 3 — pick a different idea.
- Verify fails 3 times.
- Notebook fails to execute 3 times.

## What you must NOT do

- Don't add Redis. Don't add Postgres. Don't add SQLite. Don't add Chroma / FAISS / Qdrant / Pinecone. Don't write to a filesystem JSON file as state. `verify.py` will catch you.
- Don't make memory ephemeral (in-process dicts). All state in DB.
- Don't roll your own per-user durable memory layer. Use OAMP via `oamp_helpers` (ideas 1 + 2). The hand-rolled chat history / session summary / context-card plumbing from earlier versions of this tier is gone — OAMP owns it. See `shared/references/oamp.md` for the decision tree.
- Don't write `OracleVS` boilerplate yourself — `langchain-oracledb-helper` did it.
- Don't write `oracle-database-mcp-server` boilerplate yourself — `oracle-mcp-server-helper` did it.
- Don't write `docker-compose.yml` for Oracle yourself — `oracle-aidb-docker-setup` did it.
- Don't ship without the executed notebook. Mandatory.
- Don't claim done before verify *and* notebook execution are both green.
- Don't use recursive WITH for bidirectional graphs in idea 1 if you reach for the agentic_rag 6-memory pattern. Use Python BFS over an adjacency table.
- Don't try to register a SentencePiece-tokenized ONNX model. BertTokenizer family only.
- Don't expose `run_sql` in `read_write` mode without surfacing the safety warning in the project README.
