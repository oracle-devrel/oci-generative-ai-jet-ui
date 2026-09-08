---
name: build-paths-beginner
description: Scaffold a small RAG chatbot on Oracle 26ai Free + langchain-oracledb + OCI Generative AI Grok 4 + sentence-transformers MiniLM-L6-v2 (Python-side embeddings, same model intermediate/advanced register inside Oracle) + Open WebUI. Three flavors that share one skeleton — PDF / Markdown / Web. For users new to Oracle who want a polished demo running in an afternoon.
inputs:
  - target_dir: where to scaffold (default = current working directory; ask if it isn't empty)
  - topic: optional; one of beginner/project-ideas.md, or a free-text pitch
---

The user picked the **beginner** path. Your job is to interview them, scaffold a working project that ingests a corpus and exposes a Grok-4-powered chat UI in Open WebUI, run verify, and stop. The output is a real shippable mini-product, not a tutorial.

## Step 0 — Read these references first (mandatory)

- `shared/references/sources.md`
- `shared/references/oracle-26ai-free-docker.md`
- `shared/references/langchain-oracledb.md`  ← load-bearing
- `shared/references/oci-genai-openai.md`  ← load-bearing (Pattern 1 SigV1 auth)
- `shared/references/oracledb-python.md` (skim — beginner only touches `oracledb.connect`)
- `shared/references/exemplars.md`
- `beginner/project-ideas.md`
- `skills/oracle-aidb-docker-setup/SKILL.md` — you'll invoke this
- `skills/langchain-oracledb-helper/SKILL.md` — you'll invoke this

You may not write SQL, embedder calls, or table-creation code that contradicts these files. If the user asks for something not covered, say so and stop — don't invent.

## Step 1 — Interview

Run the questions from `shared/interview.md`. For beginner specifically:

- **Q3 (DB target)** — default to "Local Docker" without re-asking.
- **Q4 (Inference)** — *not optional anymore at this tier*. **OCI Generative AI** for the LLM (Grok 4 via bearer-token). **MiniLM Python-side** for embeddings. Verify:
  - `OCI_GENAI_API_KEY` (a `sk-...` value) is set in the user's shell env OR about to be written into the project's `.env`. If neither, stop and ask the user to generate one in the OCI GenAI service console.
  - The user is OK with non-zero OCI cost (mention this once — Grok 4 is not on the always-free list).
  - Default endpoint is `https://inference.generativeai.us-phoenix-1.oci.oraclecloud.com`; the user can override via `OCI_GENAI_BASE_URL` if their key is region-locked elsewhere.
  - Embedder: `sentence-transformers/all-MiniLM-L6-v2` (384 dim) by default — runs inside the user's Python process via `HuggingFaceEmbeddings`. Same model that intermediate/advanced register inside Oracle, so corpus + chunks stay comparable across tiers.
  - Chat: `xai.grok-4` (full id required — `grok-4` alone won't resolve).
- **Q5 (Topic)** — pick one of the three from `beginner/project-ideas.md`. Map free-text pitches to the closest. If none fits, default to **idea 1 (PDFs)** and tell the user why.
- **Q6 (Notebook)** — default **no**. Beginner ships the chat UI, not a notebook walkthrough.

Print the confirmation block from `interview.md`. Don't proceed without an explicit `y`.

## Step 2 — Resolve choices

Build a scaffold spec from the interview:

| Variable | Value |
| --- | --- |
| `project_slug` | derived from topic, kebab-case: `pdf-chat`, `notes-chat`, `web-chat` |
| `package_slug` | snake_case: `pdf_chat`, `notes_chat`, `web_chat` |
| `target_dir` | from Q2; default = current working directory. Never assume a host-specific layout. |
| `embedder` | `minilm-py` (always) |
| `embedding_dim` | 384 |
| `embedding_model_id` | `sentence-transformers/all-MiniLM-L6-v2` |
| `llm_model` | `grok-4` (or fallback chosen during interview) |
| `oci_base_url` | `https://inference.generativeai.us-phoenix-1.oci.oraclecloud.com` (the OpenAI client appends `/v1`; do **not** add the legacy `/20231130/actions/openai` path — that is for SigV1, not bearer-token) |
| `collections` | `["DOCUMENTS", "CONVERSATIONS"]` |
| `has_chat_history` | `True` |
| `ingest_module` | `ingest.py` for PDFs/markdown, `add.py` for web pages |
| `entrypoint` | `python -m <package_slug>.adapter` (FastAPI on :8000); Open WebUI on :3000 talks to it |

## Step 3 — Scaffold

Order matters — invocation of building-block skills happens **before** project code.

### 3a — Foundation via building-block skills

1. **Refuse if `target_dir` is non-empty.**
2. **Invoke `skills/oracle-aidb-docker-setup`.** Pass `target_dir`. It writes `docker-compose.yml` (Oracle), `.env` (with generated `ORACLE_PWD`), brings the container up healthy. Block until it reports OK.
3. Append the **Open WebUI** service to the generated `docker-compose.yml`:
   ```yaml
   open-webui:
     image: ghcr.io/open-webui/open-webui:main
     container_name: open-webui
     ports:
       - "127.0.0.1:3000:8080"
     environment:
       - OPENAI_API_BASE_URL=http://host.docker.internal:8000/v1
       - OPENAI_API_KEY=local-stub-key
       - WEBUI_AUTH=False
     extra_hosts:
       - "host.docker.internal:host-gateway"
     volumes:
       - openwebui_data:/app/backend/data
   volumes:
     openwebui_data:
   ```
4. **Invoke `skills/langchain-oracledb-helper`.** Pass `target_dir`, `package_slug`, `embedder=minilm-py`, `collections=["DOCUMENTS", "CONVERSATIONS"]`, `has_chat_history=True`. It writes `store.py`, `_monkeypatch.py`, `history.py`, `migrations/001_chat_history.sql`. The helper will install `sentence-transformers` and pre-cache the model on first import to avoid a stall during the first user query. Block until it reports OK.

### 3b — Project-specific code (the only files this skill writes itself)

5. `target_dir/.gitignore` — extend with `data/`, `*.pdf`, `notes/`.
6. `target_dir/pyproject.toml` — extend deps:
   - Always: `fastapi>=0.110`, `uvicorn[standard]>=0.27`, `langchain-core>=0.3`, `langchain-community>=0.3`, `openai>=1.40`, `langchain-huggingface>=0.1`, `sentence-transformers>=2.7`.
   - Idea 1 (PDFs): + `pypdf>=4`.
   - Idea 2 (Markdown): + `markdown-it-py>=3`.
   - Idea 3 (Web): + `trafilatura>=1.10`, `httpx>=0.27`.
   - **Do NOT add** `oci-openai` or `openai` — friction P0-2; the OpenAI-compat path is unstable. The chat factory at `shared/snippets/oci_chat_factory.py` uses the direct OCI SDK.
7. `target_dir/.env.example` — append:
   ```
   OCI_GENAI_API_KEY=replace_me_sk_value_from_oci_genai_console
   OCI_GENAI_BASE_URL=https://inference.generativeai.us-phoenix-1.oci.oraclecloud.com
   OCI_LLM_MODEL=xai.grok-4
   EMBED_MODEL=sentence-transformers/all-MiniLM-L6-v2
   ```
   Confirm `target_dir/.gitignore` contains `.env` (the docker-setup skill adds it). **Never commit `OCI_GENAI_API_KEY`.**
8. `src/<package_slug>/inference.py` — copy `shared/snippets/oci_chat_factory.py` (chat — uses the direct OCI SDK, model id `xai.grok-4`). For the embedder, write a tiny factory:
   ```python
   from langchain_huggingface import HuggingFaceEmbeddings
   _embedder = None
   def get_embedder():
       global _embedder
       if _embedder is None:
           _embedder = HuggingFaceEmbeddings(model_name=os.environ["EMBED_MODEL"])
       return _embedder
   ```
   Cite the OCI factory at the top.
9. `src/<package_slug>/<ingest_module>` — per idea:
   - **Idea 1**: walk `data/pdfs/`, parse via `pypdf`, chunk by page + 800-token windows, `store.get_store("DOCUMENTS").add_texts(...)` with `metadata={"filename": ..., "page": ...}`. Idempotent — keep a `data/.ingested.json` ledger.
   - **Idea 2**: walk `NOTES_DIR`, chunk by H2 sections via `markdown-it-py`, metadata = `{"path": ..., "heading": ..., "frontmatter": {...}}`.
   - **Idea 3**: `python -m web_chat.add URL` — `trafilatura.fetch_url` + `extract`, chunk, metadata = `{"url": ..., "title": ..., "fetched_at": ..., "byline": ...}`.
10. `src/<package_slug>/chain.py` — LCEL chain: retriever (`get_store("DOCUMENTS").as_retriever(k=5)`) → prompt with citation instructions → `ChatOpenAI`-shaped LLM via OCI. Wrap with `RunnableWithMessageHistory(chain, get_history_factory(get_connection()), input_messages_key="question", history_messages_key="history")`. Citation format depends on idea (filename:page / file#heading / URL).
11. `src/<package_slug>/adapter.py` — FastAPI app exposing `/v1/chat/completions` (OpenAI-compatible). Body shape matches what Open WebUI sends; map `messages[-1].content` to the chain input, return assistant message in OpenAI shape. Stream via `text/event-stream`.
12. `verify.py` — copy `shared/templates/verify.template.py`, fill in:
    - `inference_enabled = True`.
    - Round-trip: `embedder.embed_query("dim check")` → assert dim == 384.
    - Smoke a single chain call against a tiny known corpus (3 lines of test text).
13. `README.md` — copy `shared/templates/readme.template.md`, fill placeholders. The "Why Oracle" paragraph names: AI Vector Search, `OracleVS`, persistent chat history (`OracleChatHistory`). Include a "Stack" section listing OCI GenAI Grok 4, `sentence-transformers/all-MiniLM-L6-v2` (Python-side, 384 dim — same model intermediate/advanced register *inside* Oracle for in-DB embeddings), `langchain-oracledb`, Open WebUI. Leave the screenshot slot for the chat UI.

## Step 4 — Verify

1. The DB is already up (skill 1 ensured this).
2. From `target_dir`: `python -m venv .venv && source .venv/bin/activate && python -m pip install -e .`.
3. `python verify.py`. Expect `verify: OK (db, vector, inference)`. The vector check asserts `len(get_embedder().embed_query("dim check")) == 384`. First run downloads the MiniLM weights (~90MB) — note this in the verify output so the user knows what's happening. On failure: follow `shared/verify.md` recovery loop, max 3 retries.
4. Bring Open WebUI up: `docker compose up -d open-webui`. Wait ~10s.
5. **Run the adapter in the background:** `python -m <package_slug>.adapter` (port 8000). Hit `http://localhost:8000/v1/models` — should return JSON listing one model. Then check `http://localhost:3000` responds (Open WebUI loaded).
6. Don't keep the adapter running — just confirm it boots cleanly. Kill it before reporting done.

## Step 5 — Polish for sharing

1. README — confirm all placeholders are filled.
2. `docs/` — leave a note: "drop a 30s demo GIF as `docs/demo.gif` showing PDF drop → ingest → chat".
3. Final report:
   ```
   Done.
     project at:    <target_dir>
     run with:      cd <target_dir>
                    docker compose up -d
                    python -m <package_slug>.<ingest_module> <args>
                    python -m <package_slug>.adapter   # blocks; Open WebUI on :3000
     verify:        OK
     ui:            http://localhost:3000  (Open WebUI)
     adapter:       http://localhost:8000/v1/chat/completions
     next:          drop your corpus, run ingest, record a 30s demo, push to GitHub.
   ```

## Stop conditions

- `~/.oci/config` missing — stop, point at `oci setup config`.
- User explicitly refuses to use OCI GenAI (cost concern, no tenancy). Tell them this tier requires it; offer to point them at the archive's old Ollama-flavored beginner ideas if they want.
- Verify fails 3 times.
- Target dir non-empty.
- The user picks a non-Oracle DB or non-Python language. Print "out of scope for v1" and stop.

## When to graduate to OAMP

If you grow this beginner project into a multi-user app — different humans hitting the same backend, each wanting their own preferences and durable facts remembered across sessions — swap the manual `OracleChatHistory` layer for **OAMP** (`oracleagentmemory` PyPI package). OAMP gives you per-user threads, automatic memory extraction, and prompt-ready context cards out of the box, and the advanced tier already wires it for you. See `shared/references/oamp.md` for the decision tree (OAMP vs. OracleVS vs. OracleChatHistory vs. plain SQL). Until then, stay on `OracleChatHistory` — single-user, full transcript visibility, no LLM-extraction cost.

## What you must NOT do

- Don't write raw `CREATE TABLE ... VECTOR(...)` DDL — `OracleVS.from_texts` (via the helper skill's bootstrap dance) handles it.
- Don't introduce Gradio, Streamlit, Flask, or any non-Open-WebUI frontend. Open WebUI + FastAPI adapter is the contract.
- Don't introduce Redis, Postgres, ChromaDB, FAISS, or any non-Oracle store — even as a fallback.
- Don't introduce Ollama as a fallback. Earlier versions of this tier supported it; the new tier is OCI-only on purpose. If the user can't use OCI, point them at `archive/beginner-ideas.md`.
- Don't write more than ~450 lines of project code total. If you're going past that, stop and reduce.
- Don't generate `ORACLE_PWD` yourself — the helper skill does it.
- Don't claim done before verify is green AND the adapter boots cleanly.
