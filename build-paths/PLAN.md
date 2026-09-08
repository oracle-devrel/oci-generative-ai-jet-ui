# `build-paths` — Design Plan

A set of agent-agnostic skill bundles that interrogate a user, pick a project at their level, and scaffold a real, runnable Oracle-AI-DB project the user can ship to social media.

This file is the spec. The skills described here don't exist yet.

---

## Goals (and non-goals)

**Goals**
- Three difficulty paths (beginner / intermediate / advanced) — *complexity gradient*, not access gating.
- Skills work in any agent harness (Claude Code, Cursor, Aider, plain GPT) — markdown-only, no harness-specific tool calls.
- Each scaffolded project is **runnable end-to-end** against a local Oracle 26ai Free container the skill helps the user start.
- Each project is **shareable**: README template, demo-friendly README structure, optional notebook.
- Skills cite *real* exemplar files from this repo and from `~/git/personal/` so the agent copies known-good patterns instead of hallucinating Oracle SQL.

**Non-goals (v1)**
- Languages other than Python.
- Hosted / paid infrastructure assumptions (everything starts local).
- Permissioning between paths (any user can pick any path).
- A web UI or interactive launcher — the skill *is* the UX.

---

## Directory layout

```
build-paths/
  README.md                          # Human-facing entry point
  SKILL.md                           # Top-level router skill: interview + path selection
  PLAN.md                            # This file
  shared/
    references/
      sources.md                     # Canonical doc URLs (frozen)
      oracle-26ai-free-docker.md     # Container setup, gotchas, healthcheck
      oracledb-python.md             # Connection pool, vector ops, gotchas
      langchain-oracledb.md          # OracleVS, retrievers, history
      oci-genai-openai.md            # OpenAI-compatible endpoint, regions, models
      ollama-local.md                # Setup, model picks, Qwen thinking-mode trap
      onnx-in-db-embeddings.md       # In-DB embeddings, no external API
      ai-vector-search.md            # VECTOR cols, indexes, similarity SQL
      hybrid-search.md               # Pre-filter / post-filter / RRF patterns
      json-duality.md                # JSON Duality views (advanced only)
      property-graph.md              # Graph + BFS-in-Python pattern (advanced only)
      visual-oracledb-features.md    # Curated feature catalog (frozen snapshot)
      exemplars.md                   # Index of real code citations (built from scans)
    templates/
      readme.template.md             # Social-shareable README skeleton
      pyproject.toml.template        # Minimal Python project metadata
      env.example                    # All env vars users might need, with comments
      docker-compose.oracle-free.yml # Drop-in Oracle 26ai Free container
      verify.template.py             # Skeleton for the verify step
      notebook.template.ipynb        # Minimal demo notebook (optional)
    interview.md                     # The questions every path asks the user
    verify.md                        # Spec for the verify step every path enforces
  beginner/
    SKILL.md
    project-ideas.md
  intermediate/
    SKILL.md
    project-ideas.md
  advanced/
    SKILL.md
    project-ideas.md
  tests/                             # gitignored — local user runs only
    .gitkeep
```

`build-paths/tests/` will be added to `.gitignore` (existing pattern: see how `apps/agentic_rag/docs/plans/` is handled).

---

## Skill model: agent-agnostic markdown

Every `SKILL.md` follows this structure so any agent can execute it:

```markdown
---
name: <slug>
description: <one-line trigger>
inputs:
  - target_dir: where to scaffold (default: ~/git/personal/<slug>-<topic>)
  - topic: optional (skips interview if provided)
---

## Step 0 — Read these references first
- shared/references/<file>.md
- shared/references/<file>.md
(Concrete file list per path. The agent loads these before writing code.)

## Step 1 — Interview
(Concrete questions. The agent must ask, not guess.)

## Step 2 — Resolve choices
(Mapping table: answer → which exemplar file to mirror.)

## Step 3 — Scaffold
(Ordered, copy-this-pattern instructions citing exemplars by path:line.)

## Step 4 — Verify
(Run shared/templates/verify.template.py adapted for the project.)

## Step 5 — Polish for sharing
(README from template, optional notebook, screenshots checklist.)

## Stop conditions
(When to stop and ask the user before continuing.)
```

**Rule for citations:** when the skill says "embed text", it must say something like "follow the pattern in `~/git/personal/oracle-aidev-template/app/vector_search.py:30-80`." No abstract pseudo-code — point at a real file.

---

## The interview (`shared/interview.md`)

Every path opens with the same 6 questions. Skills inherit and may add their own.

1. **Path?** beginner / intermediate / advanced (skip if invoked path-specific).
2. **Where should the project live?** Default `~/git/personal/<slug>`.
3. **Database target?** "Local Docker (default)" / "Already have Autonomous DB" / "Other".
4. **Inference?** beginner default = Ollama; others = "Ollama" / "OCI Generative AI (OpenAI-compatible)" / "Bring your own OpenAI-compatible URL".
5. **Project topic?** Pick from `<path>/project-ideas.md`, or describe your own.
6. **Notebook?** Yes / no (default: no for beginner, yes for intermediate, yes for advanced).

The skill **does not** proceed past Q1 without an answer. No defaults-on-everything one-shotting.

---

## Verification gate (`shared/verify.md`)

Every path's Step 4 invokes a verify routine. Spec:

- **Connect.** `oracledb.connect(...)` against the user's DSN — fails fast with a clear error (`ORACLE_PWD too short` is the #1 trap).
- **Round-trip.** Insert one known row, read it back, assert match.
- **Vector op (if topic uses vectors).** Embed one known string, run `VECTOR_DISTANCE` against itself, assert distance < 0.01.
- **Inference (if topic uses inference).** One model call with deterministic prompt; assert non-empty response.
- **Print.** Single line: `verify: OK (db, vector, inference)` or `verify: FAIL (<which step>): <error>`.

The skill is **not allowed to declare done** until verify is green. This is the difference between "shareable on social" and "embarrassing on social."

---

## The three paths

### Beginner
**Persona.** Has Python, Docker, an editor. Has not touched Oracle before. Wants to ship something in an afternoon.

**Stack.** Python + `langchain-oracledb` (`OracleVS` is the *only* DB surface a beginner touches) + Ollama (local, Qwen or Llama 3.1 8B) + Oracle 26ai Free in Docker. No FastAPI, no UI, no OCI account. Raw `oracledb` cursors are deliberately *out of scope* — the beginner sees one connection object handed to `OracleVS` and that's it.

**Why `langchain-oracledb` for beginners.** The whole point of this path is "ship something in an afternoon." `OracleVS.from_texts()` collapses table creation, embedding, and inserts into one call. The user writes 5 lines, not 50. Schema DDL, bind variables, `array.array("f", ...)` — all hidden behind the wrapper.

**Output shape.** A CLI script (~80-200 lines, smaller than the original target because the wrapper does so much) + README + `verify.py`. No notebook by default.

**The beginner's 5-line sermon.** Every project idea below collapses to:
```python
from langchain_oracledb import OracleVS
from langchain_ollama import OllamaEmbeddings

vs = OracleVS.from_texts(
    texts=[...],
    embedding=OllamaEmbeddings(model="nomic-embed-text"),
    client=conn, table_name="MY_DOCS",
    distance_strategy=DistanceStrategy.COSINE,
)
hits = vs.similarity_search("what can I make with chicken?", k=3)
```
The skill teaches that pattern first, then layers on `add_texts()` (insert more later), `similarity_search_with_score()` (see the distances), and `as_retriever()` (hook to LangChain chains for users who'll later upgrade to intermediate).

**Project ideas (in `beginner/project-ideas.md`).**
1. **Personal bookmarks search.** `from_texts()` over URL titles+descriptions → `similarity_search()`. Adds: `add_texts()` for new bookmarks. ~80 lines.
2. **Recipe finder.** Folder of `.txt` recipes → `from_texts()` → "what can I make with chicken?" Adds: filename as metadata, `similarity_search_with_score()` to show match strength. ~100 lines.
3. **Dev journal.** Append-only notes via `add_texts()` after the table exists → fuzzy recall. Adds: timestamp metadata. ~120 lines.
4. **Movie taste graph.** Plot summaries → `from_texts()` → "more like this." Adds: `as_retriever(search_kwargs={"k": 5})` to feel out the retriever interface. ~100 lines.
5. **First-vector-query smoke.** No project, just `OracleVS.from_texts(["hello world"], ...)` + one search. Confirms the stack works end-to-end in 30 lines.

**Primary exemplars to cite.**
- LangChain Oracle Vector Store usage (canonical): `apps/agentic_rag/src/OraDBVectorStore.py:1-100` — show beginners only the `from_texts` / `similarity_search` slice; flag the multi-collection wrapping as "intermediate territory."
- LangFlow component using OracleVS: `~/git/work/ai-solutions/apps/langflow-agentic-ai-oracle-mcp-vector-nl2sql/components/vectorstores/oracledb_vectorstore.py` — minimal `add_texts` + `similarity_search` example, easier to read than agentic_rag's wrapper.
- Connection (just enough to feed `OracleVS`): `~/git/personal/oracle-aidev-template/app/db.py:1-50`. The skill says "you only need this much — don't read the rest of the pool logic."
- Ollama embedder: use `langchain_ollama.OllamaEmbeddings` directly; `~/git/personal/cAST-efficient-ollama/src/cast_ollama/embedding/embedder.py:1-50` is cited only as "this is what's happening under the hood, you don't need to write it."
- Docker compose: `~/git/personal/oracle-aidev-template/docker-compose.yml:1-80`.

**What the beginner skill explicitly does NOT teach.**
- Manual `CREATE TABLE ... VECTOR(...)` DDL — `OracleVS` issues it.
- `array.array("f", qv)` bind variables — `OracleVS` handles it.
- `VECTOR_DISTANCE` SQL — `similarity_search()` wraps it.
- Connection pools — single `oracledb.connect()` is fine at this scale.

**Hard rules baked into the skill.**
- ORACLE_PWD must satisfy ≥12 chars, 1 upper, 1 lower, 1 digit — skill *generates* one and writes it to `.env`.
- Embedding model defaults to `nomic-embed-text` (768 dims). The skill never declares the column manually; `OracleVS.from_texts()` infers from the embedder.
- If user picks a Qwen model: skill sets `OLLAMA_NUM_THREAD=1` and disables thinking mode in the prompt template (known crash).
- Container healthcheck must pass before `OracleVS.from_texts()` runs (it'll otherwise error mid-DDL with a confusing connection-refused trace).
- The skill writes a one-liner `verify.py` that just does `OracleVS.from_texts(["smoke"], ...).similarity_search("smoke")` — if that returns the input, the whole stack is green.

---

### Intermediate
**Persona.** Built RAG before, probably with FAISS/Chroma. Wants to redo it on Oracle AI DB and use OCI GenAI for inference. Has an OCI GenAI API key (`sk-...`) — no full OCI tenancy needed.

**Stack.** Python + `langchain-oracledb` (the *centerpiece* — `OracleVS`, `OracleVS.as_retriever()`, `OracleSummaryStore` for chat history, multi-collection patterns) + OCI Generative AI (OpenAI-compatible endpoint, default model = Grok 4) + Gradio UI. Falls back to Ollama if user lacks OCI.

**Why `langchain-oracledb` carries the path.** Intermediate is where users build their first *real* RAG chatbot. They need: per-document-type collections, retrievers that LangChain chains can consume, conversation history that survives restarts, metadata filtering, and hybrid search. `langchain-oracledb` provides clean primitives for each — and they all sit on the *same* Oracle DB the user already started for the beginner path. Zero new infrastructure.

**LangChain features the intermediate skill explicitly teaches.**
- `OracleVS` with **multiple collections** (e.g. `PDF_DOCS`, `WEB_DOCS`, `CHAT_LOGS`) sharing one DB — pattern lifted from `apps/agentic_rag/src/OraDBVectorStore.py`.
- `OracleVS.as_retriever(search_type="similarity", search_kwargs={"k": 5, "filter": {...}})` — feeds straight into `RetrievalQA` and LCEL chains.
- **Metadata filtering** at retrieval time (`filter={"source": "manual.pdf"}`) — and the JSON-parse fix-up because Oracle returns metadata as VARCHAR2 string.
- **Hybrid search via the retriever interface.** `EnsembleRetriever([vector_retriever, bm25_retriever])` from LangChain layered on top of `OracleVS` — keeps SQL out of the user's face but gives them RRF behavior.
- **Persistent chat history.** Use `langchain-oracledb`'s message history class so conversations survive restarts; users see "stop the script, restart, the bot remembers."
- `OracleVS.add_documents()` vs `from_texts()` — when to seed once vs append continuously.
- `OracleVS.delete()` and `aget_relevant_documents()` (async path) — mentioned for users with bigger ambitions.

**Output shape.** A small package (`src/<project>/`) + Gradio app + README + notebook (recommended). ~500-800 lines, dominated by RAG glue rather than DB plumbing because LangChain handles the latter.

**Project ideas.** Each idea is paired with the LangChain primitives it forces the user to learn.
1. **PDF-RAG chatbot.** Multiple `OracleVS` collections (one per uploaded PDF or per topic) + `as_retriever()` + persistent message history. Hybrid retrieval with `EnsembleRetriever`. Mirrors `apps/agentic_rag` at smaller scale.
2. **Codebase Q&A.** Index a Git repo's source — one collection per language/dir. Metadata filter by `lang` or `path` so the user can scope questions.
3. **Web-page librarian.** Bookmarks + page-content RAG with **citations**. Uses `similarity_search_with_score` to surface confidence; metadata = source URL.
4. **Slack-thread digest.** Paste exported threads → collection per channel → summarize chains using the retriever + chat history.
5. **Personal Wikipedia.** Markdown notes folder → RAG over your second brain. Two collections: `RAW_NOTES` and `SYNTHESIZED_SUMMARIES` — agent reads from one, writes back into the other.

**Primary exemplars to cite.**
- `langchain-oracledb` multi-collection wrapper (canonical): `apps/agentic_rag/src/OraDBVectorStore.py:1-100` — the JSON-metadata monkeypatch is non-obvious; copy it.
- OpenAI-compat endpoint exposing OracleVS as `/chat/completions`: `apps/agentic_rag/src/openai_compat.py:54+`.
- LangFlow `OracleVS` component (clean `add_texts` + `similarity_search`): `~/git/work/ai-solutions/apps/langflow-agentic-ai-oracle-mcp-vector-nl2sql/components/vectorstores/oracledb_vectorstore.py`.
- LangChain hybrid retriever pattern in this codebase: `apps/limitless-workflow/src/limitless/research/vector_store.py`.
- Hybrid search SQL (for users who later want to drop below LangChain): `apps/finance-ai-agent-demo/backend/retrieval/hybrid_search.py:1-80`.
- Vector-only search SQL (same): `apps/finance-ai-agent-demo/backend/retrieval/vector_search.py`.
- OCI GenAI embeddings (Cohere): `~/git/personal/oci-genai-service/src/oci_genai_service/inference/embeddings.py:1-60`.
- OCI GenAI chat (OpenAI-compat): `~/git/personal/oci-genai-service/src/oci_genai_service/inference/chat.py:1-95`.

**Hard rules.**
- Vector column dim must match embedder — but the user never sets it; `OracleVS` derives it from the embeddings instance. Skill validates by reading `embeddings.embed_query("test")` length once before scaffolding.
- OCI auth model: bearer-token API key (`OCI_GENAI_API_KEY`, a `sk-...` value from the OCI GenAI service console) against the OpenAI-compatible endpoint at `us-phoenix-1`. No `~/.oci/config`, no compartment OCID, no SigV1 ceremony — the simpler path that drops the OCI-tenancy prerequisite for influencer demos.
- Bind variables for vectors use `array.array("f", qv)` — only relevant if the user drops below LangChain into raw `oracledb`. Skill mentions this once and moves on.
- Metadata in OracleVS comes back as VARCHAR2 string, not dict — skill *always* includes the JSON-parse monkeypatch from `OraDBVectorStore.py`. Non-negotiable; without it, downstream LangChain code silently breaks on filtered retrievals.
- One DB, many collections — the skill enforces a naming convention (`<PROJECT>_<KIND>`, e.g. `WIKI_RAW_NOTES`) so users don't collide between projects.

---

### Advanced
**Persona.** Built agents before. Wants Oracle AI DB to be the **only** state store — no Redis, no Postgres, no JSON files. Knows what episodic memory is.

**Stack.** Python + `oracledb` + `langchain-oracledb` + OCI GenAI (or Ollama) + at least 2 of: hybrid search, JSON Duality, property graph, ONNX in-DB embeddings, agent memory tables. Notebook is mandatory.

**Output shape.** Multi-module package + agent loop + tool registry + memory layer + verify suite + notebook. ~1500-2500 lines.

**Project ideas.**
1. **Personal research agent.** Ingests papers, builds a knowledge graph, recalls episodically.
2. **Code-review agent with auditable history.** Watches a repo, remembers prior reviews, learns your taste over time. **JSON Duality use case:** the agent persists each review as relational rows (`review`, `review_finding`, `review_file`) so SQL analytics work — count findings per severity, group by file, query "which functions get flagged most often." But the agent itself reads/writes one nested JSON document per review (`{review_id, repo, files: [{path, findings: [{severity, line, msg}]}]}`) because that's the natural shape for an LLM to produce and consume. The `review_dv` JSON Duality View gives both: the agent does `JSON_VALUE` reads and `@insert/@update` writes, while a Gradio dashboard runs `SELECT severity, COUNT(*) FROM review_finding GROUP BY severity` for the human. No ETL, no sync job, both views stay live.
3. **Email triage agent.** Reads inbox export, classifies, remembers sender context.
4. **"Translate-this-toy-agent-to-Oracle" path.** User points at an existing toy agent (smolagent, langgraph demo) → skill replaces its storage layer with Oracle AI DB.
5. **DevDay-style demo.** Pick 3 features from `visual-oracledb-features.md` and build a demo that shows them off.

**Primary exemplars to cite.**
- Memory manager (6 memory types, all Oracle-backed): `apps/finance-ai-agent-demo/backend/memory/manager.py:1-100`.
- Entity memory with embeddings: `apps/finance-ai-agent-demo/backend/memory/sprawl_manager.py`.
- Tool execution log: `apps/agentic_rag/src/OraDBEventLogger.py`.
- JSON Duality: `~/git/work/demoapp/api/app/routers/json_views.py:1-80`.
- Property graph + Python BFS: `~/git/work/demoapp/api/app/routers/graph.py:1-80`.
- ONNX in-DB embeddings: `~/git/personal/onnx2oracle/src/onnx2oracle/{pipeline,loader}.py`.
- Connection pool with wallet auth: `apps/limitless-workflow/src/limitless/db/pool.py:1-50`.

**Hard rules.**
- "Oracle is the only store" is enforced — skill *refuses* to scaffold Redis, Postgres, SQLite, or filesystem state.
- ONNX model must use BertTokenizer + opset ≤14 (T5/XLM-R fail at `DBMS_VECTOR.LOAD_ONNX_MODEL`).
- For graph traversal, use Python BFS over `_load_adjacency()` instead of Oracle's recursive `WITH` (cycle bug).
- Verify gate runs *all* memory types: write+read each of the 6 memory tables.

---

## Reference files: contents in brief

These are the load-bearing docs. Each is a focused 50-200 line markdown file.

| File | Contains |
| --- | --- |
| `sources.md` | One curated link list: Oracle 26ai Free download, AI Vector Search docs, OCI GenAI OpenAI-compat doc, langchain-oracledb on PyPI, ONNX runtime extensions, Ollama models. No live fetching — frozen at write time. |
| `oracle-26ai-free-docker.md` | The exact `docker-compose.yml`, ORACLE_PWD format, healthcheck, port 1521+5500, init-schema mounting, 120s startup wait. |
| `oracledb-python.md` | `create_pool` pattern, acquire/release, `array.array("f", ...)` for vectors, common ORA codes, DSN formats. |
| `langchain-oracledb.md` | OracleVS init, multi-collection pattern, the metadata-as-string monkeypatch. |
| `oci-genai-openai.md` | Endpoint URL template (`us-phoenix-1` default), bearer-token API-key recipe (canonical), SigV1/InstancePrincipal alternative, OpenAI SDK base_url. |
| `ollama-local.md` | Install, `ollama pull`, default model picks, **Qwen thinking-mode workaround** (`OLLAMA_NUM_THREAD=1`, disable `<think>` in prompts). |
| `onnx-in-db-embeddings.md` | HF → ONNX pipeline, BertTokenizer-only, opset ≤14, `DBMS_VECTOR.LOAD_ONNX_MODEL` registration, `VECTOR_EMBEDDING(text)` SQL. |
| `ai-vector-search.md` | `VECTOR(dim, FLOAT32)`, COSINE/EUCLIDEAN/DOT, `CREATE VECTOR INDEX ... TARGET ACCURACY 95`, `FETCH APPROX FIRST K ROWS ONLY`. |
| `hybrid-search.md` | Pre-filter (CONTAINS first), post-filter, RRF — three SQL templates from `hybrid_search.py`. |
| `json-duality.md` | When to use it: when the *agent* wants nested JSON and the *human dashboard* wants flat rows. Worked example: `review` + `review_finding` + `review_file` tables exposed as one `review_dv` document; `@insert @update @delete` annotations on parent + child; `JSON_VALUE` for reads, `JSON_SERIALIZE` for projection; the no-composite-keys gotcha; what fails (recursive nesting > 1 child level often needs hand-tuning). |
| `property-graph.md` | Adjacency table pattern, why Python BFS beats recursive WITH for bidirectional graphs. |
| `visual-oracledb-features.md` | Frozen catalog: vector search, hybrid search, JSON Duality, property graph, AI agents, MCP, etc. — pulled once from `jasperan.github.io/visual-oracledb`. Each feature: 1-paragraph what + when-to-use. |
| `exemplars.md` | The full citation index from the discovery scans, organized by topic. |

---

## `exemplars.md` — citation index (built from the scans)

Compact form. Each topic shows the canonical "look here first" file.

```
ORACLE CONNECTION POOL
  beginner    ~/git/personal/oracle-aidev-template/app/db.py:1-50
  fallback    ~/git/personal/cAST-efficient-ollama/src/cast_ollama/oracle_db/connection.py:1-70
  production  apps/limitless-workflow/src/limitless/db/pool.py:1-50

VECTOR INSERT + SIMILARITY
  beginner    ~/git/personal/oracle-aidev-template/app/vector_search.py:30-80
  with index  ~/git/personal/cAST-efficient-ollama/src/cast_ollama/oracle_db/operations.py:30-100
  schema DDL  ~/git/personal/cAST-efficient-ollama/src/cast_ollama/oracle_db/schema.py:10-45

LANGCHAIN ORACLEVS
  canonical   apps/agentic_rag/src/OraDBVectorStore.py:1-100
  langflow    ~/git/work/ai-solutions/apps/langflow-agentic-ai-oracle-mcp-vector-nl2sql/components/vectorstores/oracledb_vectorstore.py
  hybrid      apps/limitless-workflow/src/limitless/research/vector_store.py

OCI GENAI EMBEDDINGS (Cohere)
  canonical   ~/git/personal/oci-genai-service/src/oci_genai_service/inference/embeddings.py:1-60
  langgraph   ~/git/work/ai-solutions/apps/langgraph_agent_with_genai/src/jlibspython/oci_embedding_utils.py:1-80

OCI GENAI CHAT (OpenAI-compat)
  canonical   ~/git/personal/oci-genai-service/src/oci_genai_service/inference/chat.py:1-95
  endpoint    apps/agentic_rag/src/openai_compat.py:54+

OLLAMA EMBED
  canonical   ~/git/personal/cAST-efficient-ollama/src/cast_ollama/embedding/embedder.py:1-50
  config      ~/git/personal/cAST-efficient-ollama/src/cast_ollama/config.py:1-80

ONNX IN-DB EMBEDDINGS
  canonical   ~/git/personal/onnx2oracle/src/onnx2oracle/{pipeline,loader}.py
  test        ~/git/personal/onnx2oracle/tests/test_loader_integration.py

HYBRID SEARCH
  canonical   apps/finance-ai-agent-demo/backend/retrieval/hybrid_search.py:1-80
  vector-only apps/finance-ai-agent-demo/backend/retrieval/vector_search.py

AGENT MEMORY (DB-only)
  canonical   apps/finance-ai-agent-demo/backend/memory/manager.py:1-100
  entity      apps/finance-ai-agent-demo/backend/memory/sprawl_manager.py
  events      apps/agentic_rag/src/OraDBEventLogger.py

JSON DUALITY
  canonical   ~/git/work/demoapp/api/app/routers/json_views.py:1-80

PROPERTY GRAPH
  canonical   ~/git/work/demoapp/api/app/routers/graph.py:1-80

DOCKER COMPOSE 26ai FREE
  canonical   ~/git/personal/oracle-aidev-template/docker-compose.yml:1-80
```

**Gaps to acknowledge in the skills (don't pretend they don't exist):**
- No clean ONNX in-DB exemplar inside oracle-ai-developer-hub itself — skills point users at `~/git/personal/onnx2oracle` and that's fine.
- No JSON Duality / property-graph exemplars in `~/git/personal/` — only `~/git/work/demoapp/`. Skill cites the work-side file.

---

## README templates

`shared/templates/readme.template.md` produces social-shareable READMEs:

```
# {{project-name}}
> {{one-line pitch}} · Built with [oracle-ai-developer-hub/build-paths]({{repo-url}})

[Demo GIF placeholder — record a 30s clip with `vhs` or screen capture]

## What this is
{{2-3 lines, plain English}}

## Stack
- Oracle 26ai Free (Docker)
- {{Ollama / OCI GenAI}} for inference
- {{nomic-embed-text / Cohere v3 / ONNX in-DB}} for embeddings

## Run it (3 commands)
```
docker compose up -d
cp .env.example .env  # edit ORACLE_PWD if you want
python verify.py      # green = ready
python {{entry}}.py
```

## Why Oracle AI Database
{{auto-pulled paragraph from visual-oracledb-features.md based on topic}}

## License
MIT
```

Credit footer: `Built with the build-paths skill set from oracle-ai-developer-hub.`
No personal-name credit (per user direction).

---

## Build sequence

The order matters — references first so skills have something to cite.

1. **`shared/references/sources.md`** — link list, frozen.
2. **`shared/references/exemplars.md`** — citation index from this plan, verbatim.
3. **`shared/references/oracle-26ai-free-docker.md`** + **`shared/templates/docker-compose.oracle-free.yml`** — every path needs this; build/test it once.
4. **`shared/references/oracledb-python.md`**, **`ai-vector-search.md`**, **`ollama-local.md`** — the beginner reference set.
5. **`shared/templates/{readme.template.md, env.example, verify.template.py, pyproject.toml.template}`**.
6. **`shared/interview.md`** + **`shared/verify.md`** — the cross-cutting specs.
7. **`beginner/SKILL.md`** + **`beginner/project-ideas.md`** — first end-to-end skill, simplest case.
8. **End-to-end test of beginner** in `tests/beginner-bookmarks/` — actually run the skill against an empty dir, see what an LLM does with it. Iterate the skill until the run is clean.
9. **`shared/references/{langchain-oracledb, oci-genai-openai, hybrid-search}.md`** — intermediate reference set.
10. **`intermediate/SKILL.md`** + ideas + e2e test.
11. **`shared/references/{onnx-in-db-embeddings, json-duality, property-graph, visual-oracledb-features}.md`** — advanced reference set.
12. **`advanced/SKILL.md`** + ideas + e2e test.
13. **Top-level `README.md`** + **`SKILL.md`** (the router) — written *last*, after the three paths exist, so the router can describe them honestly.

---

## End-to-end smoke test (per path)

For each path, an empty directory + a fresh agent session must produce:

- A scaffolded project at the user's chosen target dir.
- A working `docker compose up -d` for Oracle 26ai Free.
- A `verify.py` that prints `verify: OK (...)` on first run.
- A README from the template with placeholders filled (project name, stack, why-Oracle paragraph).
- For intermediate/advanced: a `notebook.ipynb` that runs top-to-bottom without error.

The test **fails** if:
- The scaffolded code references a SQL feature not in the cited exemplar.
- The README still has `{{placeholders}}` after Step 5.
- `verify.py` is skipped or stubbed.
- Any state lands outside Oracle (advanced path only).

---

## Open questions / decisions deferred

1. **Where does the skill bundle get installed for non-Claude-Code agents?** Probably users `git clone` this repo and point their agent at `build-paths/`. Worth a `INSTALL.md` per agent (Claude Code, Cursor, Aider) once v1 is stable. Defer.
2. **Do we publish the skills to the Anthropic skill marketplace / OpenRouter skills index?** Probably yes once stable. Out of scope for v1.
3. **Versioning the skills.** Should each `SKILL.md` have a version field so users can pin? Add later — premature now.
4. **Should `tests/` ship as gitignored (per user direction) or as committed example fixtures?** Gitignored for v1; if we want shareable examples later, they go under `examples/` not `tests/`.

---

## Status

- [x] Discovery scan (personal + work) complete.
- [x] Exemplar citation index built.
- [x] This plan.
- [ ] Build sequence steps 1-13.
- [ ] First green e2e smoke test.
