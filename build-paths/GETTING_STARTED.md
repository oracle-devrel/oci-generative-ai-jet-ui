# Getting started — three worked walk-throughs

Pick a path, point Claude Code (or any agent that follows SKILL.md) at the right `SKILL.md`, answer six questions, get a runnable project. This doc walks one beginner, one intermediate, and one advanced build end-to-end so you don't have to remember anything tomorrow.

The post-restructure skill set is **OCI-Generative-AI-only** for the LLM (Grok 4 at `us-phoenix-1`, OpenAI-compat bearer-token endpoint — auth is just a `sk-...` API key, no full OCI tenancy required). Older Ollama-flavored ideas live in [`archive/`](./archive/) but aren't actively scaffolded.

---

## Once-only setup (do this before any walk-through)

Four things on your machine:

1. **Docker** — to run Oracle 26ai Free locally. Verify: `docker --version`.
2. **Python 3.11+** with `conda` (or `venv`). Verify: `python --version`.
3. **OCI Generative AI API key.** Generate one in the OCI Generative AI service console (it's a `sk-...` value). Add to your shell rc:
   ```bash
   export OCI_GENAI_API_KEY=sk-...
   ```
   The bearer-token path means **no OCI tenancy / `~/.oci/config` / compartment OCID is needed**. The key alone is enough to call Grok 4. **Never commit this value to git** — `.env` files are in `.gitignore`.
4. **The developer-hub repo cloned somewhere.** The walk-throughs reference `SKILL.md` files inside it. Pick a path you'll remember:
   ```bash
   git clone https://github.com/oracle-devrel/oracle-ai-developer-hub.git
   export HUB=$(pwd)/oracle-ai-developer-hub                  # or wherever you put it
   ```
   The walk-throughs below use `$HUB` as a stand-in. Replace it with your actual path when you paste, or `export` the variable in your shell as shown.

That's it. Oracle is started by the skill (it scaffolds `docker-compose.yml`); no separate install. Open WebUI is added to the compose file too — also no separate install.

> Each walk-through assumes you opened a fresh `claude` session in an empty project directory of your choice. The skill will scaffold *into* the current working directory, not into the hub repo.

---

## Walk-through 1 — Beginner: PDF-to-chat (idea 1)

What you'll have at the end: drop PDFs in `data/pdfs/`, get a chat UI in Open WebUI on `localhost:3000` that answers questions about them with citations. Embeddings via OCI Cohere, LLM is Grok 4. ~400 LOC.

### 1. Open Claude Code in an empty project directory

```bash
mkdir -p ./pdf-chat-poc && cd ./pdf-chat-poc            # or anywhere outside $HUB
claude
```

### 2. Tell Claude to follow the skill

Paste this exactly:

> Read `$HUB/build-paths/SKILL.md` and follow it.

Claude reads the top-level router, then asks "which path?" — answer `1` (beginner). It hands off to `beginner/SKILL.md`, which reads the references, then runs the interview.

### 3. Answer the interview

| Q | Answer |
| --- | --- |
| Q1 — Path | `beginner` (already answered above) |
| Q2 — Target dir | `.` (current directory) |
| Q3 — Database | `local Docker` |
| Q4 — Inference | OCI GenAI for the LLM (`xai.grok-4`). Confirm `OCI_GENAI_API_KEY` is set in your shell or about to land in project `.env`, you're OK with non-zero OCI cost. Default endpoint `https://inference.generativeai.us-phoenix-1.oci.oraclecloud.com`. Embedder default = `sentence-transformers/all-MiniLM-L6-v2` (Python-side, 384 dim — ~90MB downloaded once on first run). Same model intermediate/advanced register inside Oracle. |
| Q5 — Topic | `1` (PDFs) |
| Q6 — Notebook | `no` (beginner default) |

Confirm with `y` when Claude prints the summary block.

### 4. Wait for the scaffold

Claude composes from the building-block skills first:

1. **`skills/oracle-aidb-docker-setup`** — writes `docker-compose.yml`, generates `ORACLE_PWD`, brings the container up. ~90s for the first boot.
2. **`skills/langchain-oracledb-helper`** — writes `src/pdf_chat/{store,history,_monkeypatch}.py`, the chat-history migration. Smoke-tests the embedder dim (1024).

Then writes the project-specific code: `inference.py` (OCI Pattern 1 SigV1 client), `ingest.py` (PDF chunking via `pypdf`), `chain.py` (LCEL retriever → Grok 4), `adapter.py` (FastAPI `/v1/chat/completions`), `verify.py`, `README.md`.

The compose file gets the **Open WebUI** service appended. ~3-5 minutes total.

### 5. Bring up the stack

```bash
cp .env.example .env                           # set OCI_GENAI_API_KEY (NEVER commit)
docker compose up -d                           # Oracle + Open WebUI
python -m venv .venv && source .venv/bin/activate
pip install -e .
python verify.py                               # expect: verify: OK (db, vector, inference)
```

If verify fails, see troubleshooting at the bottom.

### 6. Drop PDFs and ingest

```bash
mkdir -p data/pdfs
cp ~/Downloads/*.pdf data/pdfs/
python -m pdf_chat.ingest                      # chunks + embeds; idempotent
python -m pdf_chat.adapter                     # blocks; FastAPI on :8000
```

Open `http://localhost:3000` in your browser. Pick the model (it'll be the only one). Ask a question about your PDFs. Citations like `[release_notes.pdf:p.14]` come back in the answer.

Kill the adapter, restart it, ask a follow-up — your chat history is still there. That's `OracleChatHistory`.

---

## Walk-through 2 — Intermediate: NL2SQL data explorer (idea 1)

What you'll have: a Grok-4 tool-calling agent that talks to a real Oracle schema (seeded with ~50K rows of fake but believable data) via `oracle-database-mcp-server`. Embeddings happen *inside the database* via a registered ONNX model. ~700 LOC.

### 1. New empty directory

```bash
mkdir -p ./nl2sql-poc && cd ./nl2sql-poc                # or anywhere outside $HUB
claude
```

### 2. Invoke the skill

Same paste as before:

> Read `$HUB/build-paths/SKILL.md` and follow it.

Answer `2` (intermediate) at the dispatch.

### 3. Answer the interview

| Q | Answer |
| --- | --- |
| Q1 — Path | `intermediate` |
| Q2 — Target dir | `.` |
| Q3 — Database | `local Docker` |
| Q4 — Inference | OCI GenAI for Grok 4 (`xai.grok-4`, bearer-token). **Embeddings = in-DB ONNX** (`MY_MINILM_V1`, 384 dim) registered via `onnx2oracle` CLI. Default endpoint `us-phoenix-1`. |
| Q5 — Topic | `1` (NL2SQL data explorer) |
| Q6 — Notebook | `yes` (intermediate default) |
| Q7 — sql_mode | `read_only` (idea 1 default) |

Confirm with `y`.

### 4. Wait for the scaffold

This one takes longer (~10 minutes) because of three extra steps:

1. `skills/oracle-aidb-docker-setup` brings up Oracle.
2. **ONNX export + register pipeline** runs once — exports `all-MiniLM-L6-v2` to ONNX (opset 14, BertTokenizer wrapped), copies to a host-mounted directory, then `DBMS_VECTOR.LOAD_ONNX_MODEL` registers it as `MY_MINILM_V1`. The skill smoke-tests with `SELECT VECTOR_EMBEDDING(MY_MINILM_V1 USING 'test' AS data) FROM dual` — must return a 384-vector or it stops.
3. `skills/langchain-oracledb-helper` writes `store.py` etc. with `InDBEmbeddings` (the LangChain wrapper that calls `VECTOR_EMBEDDING` via SQL).
4. `skills/oracle-mcp-server-helper` adds `oracle-database-mcp-server` to deps and writes `mcp_client.py` + `tool_registry.py`.

Then the project-specific code: `agent.py` (Grok 4 tool-calling agent), `adapter.py`, `verify.py`, `notebook.ipynb`.

Plus `migrations/100_seed_dummy.sql` — the fake schema with 10 tables and ~50K rows generated via `Faker`. Runs once at bootstrap.

### 5. Bring up the stack

```bash
cp .env.example .env                           # OCI keys, base URL pre-filled
docker compose up -d
python -m venv .venv && source .venv/bin/activate
pip install -e .
python verify.py                               # expect: verify: OK (db, vector, inference, mcp)
python -m nl2sql_explorer.adapter              # blocks; FastAPI on :8000
```

Open WebUI on `:3000`. Ask:

- "What was Q3 revenue in EU?" → agent calls `list_tables`, `describe_table`, then emits `SELECT SUM(...)`. Returns answer + the SQL it ran.
- "How many customers placed more than 5 orders last year?" → another tool-call chain.
- "Which product category has the highest return rate?" → a 3-table join, agent figures it out.

### 6. Open the notebook

```bash
jupyter lab notebook.ipynb
```

8 cells. Walks: `verify` smoke → show registered ONNX model in `USER_MINING_MODELS` → list MCP tools → direct `vector_search` call → direct `run_sql` call → one full agent turn → show `chat_history` table → "now run the adapter."

---

## Walk-through 3 — Advanced: NL2SQL + doc-RAG hybrid analyst (idea 1)

What you'll have: a production-feeling analyst that answers data questions via SQL **and** knowledge questions via vector search over your business docs (runbooks, glossary, decision docs). Knows which to pick. The agent is composed from the three building-block skills under `skills/` — your project code is just the router + agent prompt + ingest + adapter (~700 LOC). ~3-5 days of work compressed into a 15-20 minute scaffold.

### 1. New empty directory

```bash
mkdir -p ./hybrid-analyst-poc && cd ./hybrid-analyst-poc  # or anywhere outside $HUB
claude
```

### 2. Invoke the skill

```
Read $HUB/build-paths/SKILL.md and follow it.
```

Answer `3` (advanced).

### 3. Answer the interview

| Q | Answer |
| --- | --- |
| Q1 — Path | `advanced` |
| Q2 — Target dir | `.` |
| Q3 — Database | `local Docker` |
| Q4 — Inference | OCI GenAI Grok 4 + in-DB ONNX (mandatory at this tier). |
| Q5 — Topic | `1` (NL2SQL + doc-RAG hybrid analyst) |
| Q6 — Notebook | `yes` (mandatory at this tier) |
| Q7 — sql_mode | `read_only` (idea 1 doesn't need write) |
| Q8 — Demo focus | `both` (UI demo + notebook deep-dive) |

Confirm with `y`.

### 4. Wait for the scaffold

This is the longest scaffold (~15-20 minutes) because four building-block invocations happen in series:

1. `skills/oracle-aidb-docker-setup` — Oracle up.
2. ONNX export + register — `MY_MINILM_V1` registered.
3. `skills/langchain-oracledb-helper` — `OracleVS` collections = `[GLOSSARY, RUNBOOKS, DECISIONS, CONVERSATIONS]` + `OracleChatHistory`.
4. `skills/oracle-mcp-server-helper` — MCP tools = `[list_tables, describe_table, run_sql, vector_search]` (read_only).

Then project code: `router.py` (turn classifier — "data" vs "docs" vs "both"), `agent.py` (tool-calling agent with router-shaped system prompt), `ingest.py` (walks `data/{glossary,runbooks,decisions}/` and embeds into the right collections via in-DB SQL), `adapter.py` (FastAPI with streaming agent events), `verify.py` (with the **forbidden-imports grep** that fails the build if any of `redis`, `psycopg`, `psycopg2`, `sqlite3`, `chromadb`, `qdrant_client`, `pinecone`, `faiss` appear in `src/`).

Plus a 12-15 cell notebook that walks every component end-to-end.

### 5. Drop a corpus

```bash
mkdir -p data/{glossary,runbooks,decisions}
# put .md or .txt or .pdf files in each
echo "churn_score: probability a customer cancels in the next 30 days, computed nightly from..." > data/glossary/churn_score.md
echo "When EU revenue drops > 15% QoQ, check: 1) FX rate impact, 2) ..." > data/runbooks/eu_revenue_drop.md
```

### 6. Bring up the stack

```bash
cp .env.example .env
docker compose up -d
python -m venv .venv && source .venv/bin/activate
pip install -e .
python verify.py                               # expect: verify: OK (db, vector, inference, mcp, memory, no_forbidden_imports)
python -m hybrid_analyst.ingest                # one-shot
python -m hybrid_analyst.adapter               # blocks; :8000
```

### 7. Use it

Open `:3000`. Try the three modes:

- **Data:** "What was Q3 revenue in EU?" → SQL only. Returns answer + SQL.
- **Docs:** "What does churn_score mean?" → vector only. Returns answer + cite from `glossary/churn_score.md`.
- **Both:** "Explain why our EU revenue dropped last quarter using our runbooks." → router fires both: agent runs `SELECT` on the orders table to confirm the drop, retrieves from `runbooks/eu_revenue_drop.md`, synthesizes a single answer with both pieces of evidence cited.

Kill, restart, ask "summarize what we discussed" — chat history survives.

### 8. Open the notebook

```bash
jupyter lab notebook.ipynb
```

12-15 cells walking: ONNX SQL embedding round-trip → MCP tool list → router classification → vector search alone → SQL alone → routed both → memory layer dump → forbidden-imports grep proof. The last cell launches the adapter.

---

## When something goes wrong

| Symptom | What to check |
| --- | --- |
| `verify: FAIL — connect: ORA-12541` | Oracle container isn't up. `docker compose ps` should show `healthy`. Wait 60s after first `up -d`. |
| `verify: FAIL — connect: ORA-01017` | Wrong password. `.env` `ORACLE_PWD` must match what's in `docker-compose.yml`. The skill generates it; don't edit by hand. |
| `pip install -e .` fails with "no `[build-system]`" | Old scaffold. Re-run the skill. |
| Citation strings come back as raw JSON like `'{"filename": ...}'` | Metadata-as-string monkeypatch missing import. Verify `src/<pkg>/_monkeypatch.py` exists and is imported at the top of `store.py`. |
| OCI returns 401 | `OCI_GENAI_API_KEY` is missing, mistyped, or expired. Re-check the value in `.env` against the OCI GenAI service console. The endpoint is `us-phoenix-1`; if your key is region-locked elsewhere, override `OCI_GENAI_BASE_URL`. |
| ONNX `LOAD_ONNX_MODEL` fails | The model uses a SentencePiece tokenizer (T5, XLM-R, MPNet variants). Pick a Bert-family model — `all-MiniLM-L6-v2` is the safe default. |
| `VECTOR_EMBEDDING` returns wrong dim | Drop the model: `BEGIN DBMS_VECTOR.DROP_ONNX_MODEL('MY_MINILM_V1'); END;` then re-run the export. |
| MCP server hangs at startup | Check `oracle-database-mcp-server` is on PATH after `pip install -e .`. The MCP server inherits `DB_DSN`/`DB_USER`/`DB_PASSWORD` from env — verify those are exported. |
| Open WebUI can't reach the adapter | `host.docker.internal:host-gateway` extra-host is the bridge. On older Docker Desktops you may need to swap for the host's actual LAN IP. |
| Forbidden-imports check fails (advanced) | You imported one of `redis`/`psycopg`/`psycopg2`/`sqlite3`/`chromadb`/`qdrant_client`/`pinecone`/`faiss` somewhere. Find it: `grep -RE 'import (redis\|psycopg\|psycopg2\|sqlite3\|chromadb\|qdrant_client\|pinecone\|faiss)' src/`. Replace with the Oracle equivalent. |

If you're really stuck: re-read the `README.md` the scaffold wrote in your project — it's tailored to your choices and has the exact commands.

---

## What if I want a different idea within a tier?

Same flow. At Q5, pick a different number from `build-paths/{beginner,intermediate,advanced}/project-ideas.md` (each has 3 ideas). Or pitch your own in free text — the skill maps it to the closest of the three and confirms.

## What if I want to invoke just one of the building-block skills?

You can. For example, to bring up Oracle 26ai Free in any project (without the rest of the build-paths scaffold):

> Read `$HUB/build-paths/skills/oracle-aidb-docker-setup/SKILL.md` and follow it.

The skill asks its own inputs, runs its own steps, and reports back. Useful when you're bolting Oracle onto an existing app.

---

## TL;DR cheat sheet (rip this out)

```
1. mkdir empty-dir && cd empty-dir && claude
2. "Read $HUB/build-paths/SKILL.md and follow it."
3. Answer 6-8 questions:
     - path:        beginner | intermediate | advanced
     - target_dir:  .
     - database:    local Docker
     - inference:   OCI GenAI (auto: Cohere for beginner, in-DB ONNX for intermediate/advanced)
     - topic:       1 | 2 | 3 (per tier)
     - notebook:    no (beginner) | yes (intermediate) | yes mandatory (advanced)
     - sql_mode:    read_only (intermediate, advanced 1+2) | read_write (advanced 3, requires explicit y)
     - demo_focus:  polished_ui | deep_dive | both (advanced only)
4. cp .env.example .env  # set OCI_GENAI_API_KEY (NEVER commit)
5. docker compose up -d
6. python -m venv .venv && source .venv/bin/activate && pip install -e .
7. python verify.py        → expect: verify: OK
8. python -m <pkg>.<ingest if needed> ; python -m <pkg>.adapter
9. open http://localhost:3000
```

That's the whole thing.
