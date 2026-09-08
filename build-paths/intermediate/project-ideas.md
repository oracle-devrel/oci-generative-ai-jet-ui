# Intermediate — project ideas

Three projects that give an LLM agent **live access to an Oracle schema** via the `oracle-database-mcp-server`, with embeddings happening **inside the database** (registered ONNX model, no external embedding API). Powered by Grok 4 on OCI Generative AI for chat.

The skill maps free-text pitches to the closest of the three. If nothing maps, default to **idea 1 (NL2SQL)** — it's the most universal demo.

---

## Why in-database ONNX embeddings (not OCI Cohere)

This tier deliberately moves off external embedding APIs and onto **`VECTOR_EMBEDDING(MODEL USING text AS data)`** inside Oracle. The reasons matter — make sure the user understands them:

| In-DB ONNX wins | Detail |
| --- | --- |
| **Zero embedding round-trips on insert** | `INSERT INTO docs (content, embedding) VALUES (:c, VECTOR_EMBEDDING(MODEL USING :c AS data))` does tokenize → forward pass → store in one statement. Bulk loads run an order of magnitude faster than the embed-then-bind Python pattern. |
| **Same model on insert and on query** | Drift between insert-time embedder and query-time embedder is a real bug class with external APIs (model version changes, regional model swaps). With one registered ONNX model, this is impossible by construction. |
| **No data egress** | Sensitive content never leaves the DB. With Cohere or OpenAI, every embed call ships the text to a third-party endpoint. For "embed the user's notes / contracts / personal data" use cases this matters. |
| **No process to babysit** | No Ollama, no Cohere quota, no DashScope rate limit, no `nomic-embed-text` daemon. The DB is the embedder. |
| **Pure-SQL vector search** | `SELECT id FROM docs ORDER BY VECTOR_DISTANCE(embedding, VECTOR_EMBEDDING(MODEL USING :q), COSINE) FETCH FIRST 5 ROWS` works without Python. The MCP server's `vector_search` tool literally executes this. |

The trade: a one-time pipeline cost (HF → ONNX export → opset-14 → wrap with tokenizer → `LOAD_ONNX_MODEL`). The skill scaffolds this from `shared/snippets/onnx_loader.py` plus the export pattern documented in `shared/references/onnx-in-db-embeddings.md`. After the registration, the user's app code calls `embed_query(...)` and the `Embeddings` subclass turns into one SQL statement.

**Default model:** `sentence-transformers/all-MiniLM-L6-v2` — 384-dim, BertTokenizer (Oracle's `onnxruntime_extensions` only ships Bert), 90MB on disk, fits the free-tier model size cap. Multilingual users can swap to `paraphrase-multilingual-MiniLM-L12-v2` (also Bert tokenizer) at cost of slower throughput.

The skill verifies the dim consistency (384) at `verify.py` time and refuses to scaffold app code if the registered model's output dim doesn't match.

---

## Stack (same for all three)

| Layer | Choice |
| --- | --- |
| DB | Oracle 26ai Free in Docker (via `skills/oracle-aidb-docker-setup`) |
| Vector store | `OracleVS` with `InDBEmbeddings` (subclass that calls `VECTOR_EMBEDDING(...)` via SQL) |
| Embeddings | `MY_MINILM_V1` (registered ONNX model, 384 dim) |
| LLM | OCI GenAI `xai.grok-4` at `us-phoenix-1`, OpenAI-compat bearer-token API key (`OCI_GENAI_API_KEY=sk-...`) |
| Tools | `oracle-database-mcp-server` over stdio, exposing `list_tables`, `describe_table`, `run_sql`, `vector_search` (read-only by default) |
| Agent | LangChain tool-calling agent (`llm.bind_tools(get_tools())` + `RunnableWithMessageHistory`) |
| UI | Open WebUI on `:3000`, talks to a FastAPI adapter on `:8000` |
| Chat history | `OracleChatHistory` table |

`skills/oracle-aidb-docker-setup` brings the DB up. `skills/langchain-oracledb-helper` writes `store.py` + `_monkeypatch.py` + `history.py` + `migrations/`. `skills/oracle-mcp-server-helper` writes `mcp_client.py` + `tool_registry.py`. The intermediate `SKILL.md` then writes `agent.py`, `adapter.py`, `ingest.py` — that's it. ~600-800 LOC of project-specific code per idea.

---

## 1. NL2SQL data explorer (with seeded fake data)

**Pitch.** Point the agent at a real Oracle schema. Ask it questions in natural language. It picks the right MCP tool, runs the SQL, returns the answer alongside the SQL it ran.

**Seed data.** The skill scaffolds a fake-but-believable schema (10 tables — customers, orders, products, employees, suppliers, invoices, payments, regions, categories, returns) populated with ~50K rows of realistic dummy data via `Faker`. Lives in `migrations/100_seed_dummy.sql` (executed once at bootstrap). Lets the user demo the project before they have their own data.

**Agent loop.**

```
user: "what was Q3 revenue in EU?"
  → llm.bind_tools([list_tables, describe_table, run_sql, vector_search])
  → agent calls list_tables → sees `orders`, `regions`
  → calls describe_table("orders") → notes columns
  → emits run_sql("SELECT SUM(total) FROM orders ... WHERE region IN (SELECT id FROM regions WHERE name='EU') AND quarter='Q3'")
  → returns: "EU Q3 revenue was $4.2M.
              I ran: <SQL>"
```

**Distinct primitive taught.** **Tool-calling agent over live SQL.** The user sees the agent reason about the schema, not just chat about pre-ingested docs. Demonstrates Grok 4's tool-call quality and exposes how MCP gives the LLM a typed contract for `run_sql` (parameter validation, result schema).

**LOC.** ~700 — most of it is the `agent.py` tool-call loop and the seed SQL.

**Demo.** Spin up, ask 5 questions about the dummy schema, screenshot the SQL-with-answers transcript. Then point at the user's real Oracle (change `DB_DSN` in `.env`, rerun) — same agent, real data.

---

## 2. Schema doc generator + Q&A

**Pitch.** Agent walks the schema (via MCP), generates plain-language descriptions for each table and column, persists them as in-DB embeddings, then RAGs over its own generated docs.

**Two-phase shape.**

*Phase A — generation (one-shot, runs once per schema):*
```
python -m schema_doc.generate
  → list_tables → for each table:
    → describe_table → grok-4 prompt: "describe this table in 2 sentences for a non-DBA"
    → INSERT into SCHEMA_DOCS_DOCUMENTS (table_name, column, description, embedding)
       — embedding via VECTOR_EMBEDDING(MY_MINILM USING :description)
```

*Phase B — chat (interactive):*
```
user: "what's the difference between customer.status and subscription.state?"
  → similarity_search over SCHEMA_DOCS_DOCUMENTS via MCP vector_search
  → grok-4 with retrieved chunks → cited answer
```

**Distinct primitive taught.** **Agent that writes back to its own vector store.** The agent isn't just retrieving — it generated the corpus by calling MCP tools. Sets up the advanced "self-improving research agent" pattern. Also: this is where the in-DB ONNX win is most obvious — the agent can `INSERT INTO ... VALUES (..., VECTOR_EMBEDDING(...))` in a single SQL statement, no Python embedder roundtrip per generated description.

**LOC.** ~600 — the generation script is shorter than the agent loop because there's no per-turn tool selection.

**Demo.** Run against the seed schema from idea 1. Show the `SCHEMA_DOCS_DOCUMENTS` table populated. Ask 3 schema-design questions. Show the citations point at real table+column pairs.

---

## 3. Hybrid retrieval (vector + SQL)

**Pitch.** Two corpora in the same DB — unstructured docs (PDFs about your product) AND structured records (your `invoices` table). Agent has both vector search MCP tools AND SQL MCP tools. Picks the right combo per question.

**Two collections, one prompt.**

| Collection | What's in it | How agent reaches it |
| --- | --- | --- |
| `INVOICES_DOCS` (`OracleVS`, in-DB embeddings) | PDFs of invoices, contracts, attached emails | `vector_search(collection="INVOICES_DOCS", q="...")` MCP tool |
| `invoices` (relational, normal Oracle table) | Per-invoice rows: amount, date, customer_id, status | `run_sql(...)` MCP tool |

**Agent loop.**

```
user: "show me invoices like the one I uploaded last quarter — same customer, same line items, but ones I haven't paid yet."
  → agent calls vector_search to find PDFs matching the user's reference doc
    (returns invoice_ids: [1241, 1389, 1505])
  → agent calls run_sql:
       SELECT i.id, i.amount, i.due_date
       FROM invoices i
       WHERE i.id IN (1241, 1389, 1505) AND i.status = 'unpaid'
  → returns: structured table + the PDF previews from the vector hits.
```

**Distinct primitive taught.** **Cross-modal retrieval with the same DB as the substrate.** Demonstrates Oracle's pitch — vector and relational and chat history live in one store, joinable in one query. With Postgres + Pinecone + Redis you couldn't do this in one round-trip.

**LOC.** ~800 — the longest of the three because the agent prompt has to teach Grok 4 when to pick vector vs SQL vs both.

**Seed data.** Reuses idea 1's seed schema, plus a new `INVOICE_PDFS/` folder with 20 fake invoice PDFs (generated by the skill via `reportlab` during bootstrap), embedded into `INVOICES_DOCS` at ingest time.

**Demo.** Two parallel queries:
- "what's the total amount across all my unpaid Q3 invoices?" → SQL only.
- "find an invoice that mentions 'expedited shipping' clauses" → vector only.
- "find unpaid invoices similar to this one (uploads PDF)" → vector + SQL joined.

---

## What the skill won't scaffold at this tier

- **`run_sql` in read_write mode without explicit confirmation.** Even with confirmation, the skill warns prominently — letting an LLM mutate your schema is a footgun.
- **Vector indexes other than HNSW.** Oracle 26ai supports IVF too, but at this tier HNSW is the safe default. Tier 3 may swap.
- **Hybrid (vector + BM25) retrieval inside one query.** That's hybrid-search-the-search-technique, different from "hybrid (vector + SQL) retrieval"-the-architecture above. If the user wants BM25 + vector ensemble, the skill points at the archive's old PDF-RAG idea.
- **Anything that needs a JS frontend.** Open WebUI is the UI; if the user wants something custom, that's tier 3 territory.
- **Anything where Oracle isn't the only store.** Same constraint as the original five. No FAISS, no Chroma, no Postgres for chat history — all of that is `OracleChatHistory`.
- **Multi-tenant auth.** Single-user only.

---

## What you get (sanity check)

By the time `verify.py` reports OK, the user has:

- A healthy Oracle 26ai Free container.
- A registered `MY_MINILM_V1` ONNX model in the DB (verified by a `VECTOR_EMBEDDING(MY_MINILM USING 'test' AS data) FROM dual` smoke).
- An `oracle-database-mcp-server` process speaking stdio to their Python.
- A FastAPI adapter (`:8000`) wrapping a Grok-4 tool-calling agent.
- Open WebUI on `:3000` pointed at the adapter.
- A populated seed schema (idea 1, 3) or schema-docs collection (idea 2).
- A README with the OCI cost note + the in-DB embeddings explainer.

That's the deliverable. The user should be able to record a 60-second demo of the agent reasoning about real-looking data.
