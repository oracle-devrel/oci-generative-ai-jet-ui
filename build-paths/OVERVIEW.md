# build-paths: overview

## What it is

A skill set that takes a developer (typically an influencer who's going to build something on Oracle AI DB and post about it), interrogates them with 6-8 questions, picks a project at their level, and scaffolds a real and runnable application powered by Oracle AI Database + OCI Generative AI.

The scaffold is not a tutorial. It produces:

- A working Docker stack (Oracle 26ai Free + Open WebUI - in case there's a front end involved in the development of the chosen use case).
- A `verify.py` that proves end-to-end correctness before declaring that the implementation using this system is done.
- Application code (FastAPI adapter, agent loop, ingest scripts, chat history).
- A README pre-filled with "Why Oracle" content tied to the features the project actually uses.
- (Intermediate / advanced) a Jupyter notebook that walks the project cell-by-cell.

The goal: an influencer can record a 30-second to 3-minute demo within a day (beginner) to a week (advanced), without having to have fought against official docs or spent an unnecessary amount of time reading through documentation about Oracle SQL, the LangChain integration, or the MCP server plumbing from scratch: we ease the development efforts of the influencers.

It's **agent-agnostic**: every skill is markdown, the agent (Claude Code, Cursor, Aider, anything that follows `SKILL.md`) does the work. We don't ship a CLI; we ship instructions.

---

## How it's built

Five layers, top to bottom:

```text
build-paths/SKILL.md           ← top-level router. Asks "which path?"
                                      Hands off to one of the three tier skills.

build-paths/{beginner,intermediate,advanced}/SKILL.md
                                    ← per-tier orchestration.
                                      Runs the interview, picks an idea,
                                      composes the building-block skills,
                                      writes the project code.

build-paths/skills/            ← reusable building blocks. Three skills.
  oracle-aidb-docker-setup/          (Docker compose, container up, healthy)
  langchain-oracledb-helper/         (OracleVS, OracleChatHistory, monkeypatch)
  oracle-mcp-server-helper/          (oracle-database-mcp-server + tool wiring)

build-paths/shared/            ← references, snippets, templates.
  references/                        (langchain-oracledb, oci-genai, onnx-in-db, ...)
  snippets/                          (verbatim code: monkeypatch, OCI factory, ONNX loader)
  templates/                         (docker-compose, pyproject, README, verify.py)
  interview.md                       (the six core questions every tier asks)

build-paths/{beginner,intermediate,advanced}/project-ideas.md
                                    ← three project ideas per tier, with shapes
                                      and primitives explicitly called out.
```


This means:
- Less boilerplate per project.
- One source of truth for the Oracle layer (fix a bug in `langchain-oracledb-helper` once, every project benefits).
- The building-block skills are themselves invokable standalone — useful when someone wants to bolt Oracle onto an existing app.

### Universal stack (post-restructure)

| Layer | Choice | Why |
| --- | --- | --- |
| DB | Oracle 26ai Free in Docker | Single command up; vector + relational + JSON in one place. |
| LLM | OCI Generative AI `xai.grok-4` (`us-phoenix-1`, OpenAI-compat bearer-token endpoint) | Hosted, fast, no GPU on the laptop. Auth is a single `sk-...` API key (`OCI_GENAI_API_KEY`) — **no OCI tenancy / `~/.oci/config` / compartment OCID needed**. *All three tiers* require this. |
| UI | Open WebUI (`:3000`) → FastAPI adapter (`:8000`) | Polished out of the box, OpenAI-compatible, drop-in for ChatGPT-style interaction. The adapter is the thinnest possible glue. |
| Vector store | `langchain-oracledb` `OracleVS` | The library we're showcasing. |
| Chat history | `OracleChatHistory` (custom subclass — `langchain-oracledb` doesn't ship one) | Survives kill / restart. |
| Embeddings | Tier-dependent (see below) | |

### Embeddings (one model, two homes)

All three tiers use the **same embedding model** — `sentence-transformers/all-MiniLM-L6-v2` (384 dims). What changes between tiers is *where the inference runs*.

| Tier | How embeddings happen | Dim | Why |
| --- | --- | --- | --- |
| Beginner | Python-side via `HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")` | 384 | The user runs `pip install sentence-transformers` and that's the whole embedder setup. Model weights are tiny (~90MB), no daemon, no API key, no quota. First-time download is one-shot. |
| Intermediate | **In-DB ONNX** — `MY_MINILM_V1` registered via `DBMS_VECTOR.LOAD_ONNX_MODEL`, called as `VECTOR_EMBEDDING(MY_MINILM_V1 USING text AS data)` | 384 | The pedagogical centerpiece of this tier. Same model, but now Oracle does the inference inside the DB. The user's corpus, chunk sizes, and retrieval results stay comparable to what they built at tier 1; only the embedding location changes. |
| Advanced | Same in-DB ONNX | 384 | Required by the "Oracle is the only state store" rule. |

Keeping one model across tiers means: same dim, same tokenizer, same chunk-size sweet spot. A user who builds the beginner project then the intermediate one doesn't re-tune anything — they migrate the *same corpus* and watch the embedding step move from Python into SQL.

### Why in-DB ONNX matters (for intermediate / advanced)

- **Zero embedding round-trips on insert.** Bulk loads run an order of magnitude faster than the embed-then-bind Python pattern.
- **Same model on insert and query.** No drift between insert-time and query-time embedders.
- **No data egress.** Sensitive content never leaves the DB.
- **No second process to babysit.** No `sentence-transformers` Python process holding GPU/CPU memory; the DB is the embedder.
- **Pure-SQL vector search.** The MCP server's `vector_search` tool is one SQL statement.

The one-time cost: an export pipeline (HF → ONNX, opset 14, BertTokenizer wrap, `LOAD_ONNX_MODEL`). The skill scaffolds this from the local `shared/snippets/onnx_loader.py` plus the documented export pattern in `shared/references/onnx-in-db-embeddings.md` so the user doesn't write any of it.

---

## The three paths

Three difficulty levels, three project ideas per tier, designed depth-first not breadth-first.

> **Oracle is the protagonist.** Every project across every tier exists to highlight what Oracle AI Database does, not to teach generic LLM-app patterns. Pitching, demoing, and writing the README all foreground the Oracle component the project leans on. Things like "PDF chunking" or "URL fetching" are scaffolded glue, not the story.

### Beginner — three "X-to-chat" flavors (~1 afternoon)

Same skeleton across all three; what differs is the source corpus. The user picks based on what data they have lying around. **What every beginner project showcases:** `langchain-oracledb` `OracleVS` as the vector store, AI Vector Search over MiniLM embeddings (Python-side at this tier — same model that gets registered inside Oracle in tier 2), and `OracleChatHistory` keeping conversation state inside the DB across kill/restart.

| Idea | Pitch | Oracle features highlighted |
| --- | --- | --- |
| 1. PDFs-to-chat | Drop PDFs, chat about them with citations. | `OracleVS` single-collection vector search; Oracle stores the page-level metadata so citations resolve back to filename + page. |
| 2. Markdown-to-chat | Point at Obsidian / Logseq notes, chat. | `OracleVS` with H2-section chunks; markdown frontmatter (`tags`, `date`) stored as Oracle metadata to prefigure tier-2 filtered retrieval. |
| 3. Web-pages-to-chat | Pocket replacement, `add.py URL`. | `OracleVS.add_documents` per page (vs bulk); rich URL/byline metadata on the Oracle row, plus `similarity_search_with_score` to surface confidence directly from the DB. |

Output: ~350-450 LOC. Open WebUI on `:3000`, FastAPI adapter on `:8000`, Grok 4 answers questions about the user's corpus with citations sourced from Oracle.

### Intermediate — three Oracle-MCP-flavored agents (~1-2 days)

The user has built RAG before. This tier puts the spotlight squarely on two Oracle-only patterns: **`oracle-database-mcp-server`** giving the agent live SQL + schema introspection as tools, and **`VECTOR_EMBEDDING(MODEL USING text)`** producing embeddings inside the database via a registered ONNX model (no external embedding API, no data egress).

| Idea | Pitch | Oracle features highlighted |
| --- | --- | --- |
| 1. NL2SQL data explorer | Live Oracle schema (seeded with ~50K Faker rows), NL questions, agent picks `list_tables` → `describe_table` → `run_sql`. Returns the SQL it ran. | `oracle-database-mcp-server` exposing the DB as typed tools to Grok 4; in-DB ONNX embeddings (`MY_MINILM_V1`) used wherever the agent needs vector hits. |
| 2. Schema doc generator + Q&A | Agent walks the schema, generates descriptions, embeds them in-DB, RAGs over its own generated docs. | `INSERT INTO ... VALUES (..., VECTOR_EMBEDDING(MY_MINILM_V1 USING :description))` — the entire generation step is one SQL round-trip per row, no Python embedder in the loop. Demonstrates "Oracle as the embedding engine." |
| 3. Hybrid retrieval (vector + SQL) | One question, two corpora in the same DB: invoice PDFs (vector) + invoice rows (relational). Agent fans out, joins on `customer_id`. | One Oracle store covering vector + relational + chat history, joinable in one query. The pitch you can't make with Postgres + Pinecone + Redis. |

Output: ~600-800 LOC per project. Same Open WebUI + FastAPI shape, plus a Jupyter notebook walkthrough.

### Advanced — three projects composed from the skills/ library (~3-5 days)

Constraint: **Oracle is the only state store.** The advanced tier's whole pedagogical point is "what becomes possible when you commit to Oracle for *all* persistence." Each project's own `SKILL.md` writes only application logic; the Oracle layer comes from the [`skills/`](./skills/) building blocks. `verify.py` greps for forbidden imports (`redis`, `psycopg`, `sqlite3`, `chromadb`, `qdrant_client`, `pinecone`, `faiss`) and fails the build if any sneak in.

| Idea | Pitch | Oracle features headlined |
| --- | --- | --- |
| 1. NL2SQL + doc-RAG hybrid analyst | Live schema + business docs in one agent, routed per question. The "what would I actually ship at work" angle. | Multi-collection `OracleVS` (glossary, runbooks, decisions) + `oracle-database-mcp-server` for SQL + `OracleChatHistory` — three Oracle subsystems converging in one router. |
| 2. Self-improving research agent | Long-running tasks; agent writes back its own tool calls + summaries; future runs retrieve from that history before deciding next moves. | **Oracle as agent memory.** Toolbox table (relational), execution log (`OracleVS`), session summaries (`OracleVS`). All three memory types live in the DB; the agent's "self" persists in Oracle, not in Redis or a JSON file. |
| 3. Conversational schema designer | Talk about your domain; agent designs the schema, runs DDL via MCP (with confirmation gating), generates JSON Duality views, seeds data, lets you query. | **JSON Duality** as the headline (`CREATE OR REPLACE JSON RELATIONAL DUALITY VIEW ... WITH INSERT UPDATE DELETE`) + DDL-via-MCP in `read_write` mode + `DESIGN_HISTORY` table that makes every step replayable on a fresh DB. The most "Oracle-only could do this" demo in the catalog. |

Output: ~500-700 LOC of project code (the rest is the building blocks). Mandatory notebook. Grok 4 only.