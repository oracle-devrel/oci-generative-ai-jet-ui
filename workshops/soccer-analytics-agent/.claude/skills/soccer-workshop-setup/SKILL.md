---
name: soccer-workshop-setup
description: Bootstrap the soccer analytics agent workshop. Starts the Oracle AI Database Free container, applies schema, loads the FIFA dataset, optionally trains models, populates LangChain OracleVS hybrid retrieval plus semantic memory, applies LangGraph OracleDB observability, and verifies OCI GenAI access. Use when starting the workshop or resetting a stale environment.
---

# Soccer Workshop Setup

You are bootstrapping the soccer-analytics-agent workshop. Follow these steps strictly in order. Stop and surface the error on any failure.

Each step has a "**If it fails:**" hint pointing at the most common root cause we hit while building this. Skim them once before running so you know what to watch for.

## Hybrid retrieval contract

This workshop is hybrid-first after ML inference. Coding agents must build and verify the LangChain OracleVS vector store (`SOCCER_LANGCHAIN_DOCS`) after `PREDICCIONES_FINAL` is loaded, and the final Grok 4 chat must ground explanatory answers with `hybrid_retrieve` or the startup `hybrid_search(...)` context before falling back to semantic-only memory. `vector_search` remains in the workshop as the baseline contrast: semantic similarity over `semantic_memory` only, without cached prediction documents or keyword/text scoring.

## LangGraph OracleDB observability contract

Every workshop build must also initialize `langgraph-oracledb` `OracleStore` tables and prove the agent stores individual execution steps in Oracle. The current agent remains a small Grok prompt-protocol loop, but each turn writes ordered step records (`turn_start`, `grounding_retrieved`, `model_response`, `tool_call`, `tool_result`, `final_response`) into the LangGraph OracleDB store under namespace `("soccer-agent", "agent-steps", session_id)`. The API exposes these rows at `GET /observability/{session_id}` for demo/debugging.

## Required workshop-day OCI values

The Grok 4 final chat is a required workshop capability, so setup must not silently proceed with placeholder OCI values. When building the workshop, inspect `.env` after it exists. If any of these three values are missing or still contain `REPLACE_ME`, ask the user to provide them before running `scripts/verify.py`, `scripts/smoke_test.py`, or declaring the workshop ready:

1. `OCI_GENAI_ENDPOINT` — regional OCI GenAI Inference endpoint.
2. `OCI_GENAI_API_KEY` — bearer API key beginning with `sk-`.
3. `OCI_COMPARTMENT_ID` — compartment OCID used in the GenAI request body.

If the user says they will provide these on the day of the workshop, leave placeholders in `.env`/`.env.workshop.local`, complete only the local Oracle/data/model setup, and explicitly report that Grok verification, smoke testing, and final public readiness remain blocked until those three values are pasted locally. Never write real OCI values into tracked files.

## Steps

1. **Check the container engine (Docker or Podman)**
   - The setup script auto-detects Docker (preferred) or Podman, so either works. To confirm one is present:
     - Run: `docker info >/dev/null 2>&1 && echo docker || (podman info >/dev/null 2>&1 && echo podman)`
   - **If it prints neither:** install Docker (https://docs.docker.com/get-docker/) or Podman (https://podman.io/). On Docker, make sure the daemon is running and the user is in the `docker` group. Don't try to fix it from inside Claude Code — surface it.

2. **Ensure `.env` exists and gate on required OCI values**
   - If `.env` is missing at the repo root, copy from `.env.example`.
   - Inspect `.env` for `OCI_GENAI_ENDPOINT`, `OCI_GENAI_API_KEY`, and `OCI_COMPARTMENT_ID`. If any are missing or still contain `REPLACE_ME`, ask the user for those exact three values. The instructor may say they will provide them on workshop day; in that case, keep placeholders and continue only through local setup, but do not claim Grok/final readiness until they are supplied.
   - Oracle values use the defaults that match `docker/docker-compose.yml`.
   - Never write real OCI values into tracked docs or examples; keep them in local ignored `.env` or `.env.workshop.local` only.
   - **If it fails:** stray BOM or wrong line endings in `.env` will make `python-dotenv` silently load nothing. Save as plain UTF-8 LF.

3. **Start the Oracle container**
   - Run: `bash .claude/skills/soccer-workshop-setup/scripts/01_start_oracle.sh`
   - The script auto-detects Docker or Podman, picks an Apple-Silicon-native image on arm64 Macs (and the official amd64 image everywhere else), then polls until the container is healthy (up to 7.5 min).
   - **If it fails on port `1525`:** another container is bound to host port `1525`. Check `docker ps` (or `podman ps`). The compose file deliberately picks `1525` because `1521`-`1524` are commonly taken; if `1525` is also taken you need to edit `docker-compose.yml` and `ORACLE_DSN`.
   - **If it fails on an Apple Silicon Mac with an image/platform error:** the launcher should have selected `gvenzl/oracle-free:latest`. Confirm `uname -m` reports `arm64`; if you are forcing the official image via `ORACLE_IMAGE`, unset it and re-run.

4. **Create the soccer user with workshop grants**
   - Run: `bash .claude/skills/soccer-workshop-setup/scripts/setup.sh`
   - Idempotent: drops then recreates the user.
   - **Required grants are not just CONNECT/RESOURCE.** `CREATE MINING MODEL` is also granted here — without it, step 8 below fails with `ORA-01031: insufficient privileges` deep inside `DBMS_VECTOR.LOAD_ONNX_MODEL`. Do NOT remove that grant.

5. **Load match data**
   - Run: `uv run python scripts/setup_db.py`
   - This needs CSV files (`results.csv`, `goalscorers.csv`, `shootouts.csv`) in `data/`.
   - **Canonical source (always use this — no substitutes):** https://www.kaggle.com/datasets/martj42/international-football-results-from-1872-to-2017 (CC0). Download with `kaggle datasets download -d martj42/international-football-results-from-1872-to-2017 -p data/ --unzip` (needs `~/.kaggle/kaggle.json`), or fetch the ZIP from the URL and unzip into `data/`.
   - **Stub-data path:** if `results.csv` is < 1 KB the workshop will still run, but later steps (`embed_match_facts.py`, ML feature engineering, bulk predictions) will produce mostly empty output. Do not "fix" zero-row counts in stub mode — load the real Kaggle dataset instead.

6. **Prepare model artifacts**
   - Run: `uv run python scripts/prepare_artifacts.py`
   - The hub workshop ships production artifacts in `models/`. This step validates those files and falls back to training from the loaded Oracle data only if the artifacts are missing or invalid.
   - **If it fails:** `MATCH_RESULTS`/`GOALSCORERS` were not loaded, dependencies are missing, or the local machine cannot train the XGBoost model. Re-run step 5 and inspect the training error.

7. **Apply memory schema and LangGraph observability store**
   - Run: `uv run python scripts/init_memory.py`
   - This recreates the custom memory tables and calls `langgraph-oracledb` `OracleStore.setup()` so the Oracle-backed step-observability tables exist before the app starts.
   - **If it fails:** the script drops custom memory tables in dependency order and recreates them. If it stops mid-way you may have a half-applied schema; just re-run it. If the failure mentions `langgraph-oracledb`, confirm the uv environment installed the package from `pyproject.toml`/`uv.lock`.

8. **Load the ONNX embedding model** (~30-90s)
   - Run: `uv run python scripts/load_onnx_model.py`
   - First run downloads from HuggingFace and uploads the augmented ONNX to Oracle.
   - **Why this is the trickiest step:** Oracle AI Database's `VECTOR_EMBEDDING(...)` SQL function expects an ONNX model with the tokenizer **baked into the graph**, NOT a vanilla transformer export. We learned this the hard way:
     - HuggingFace `optimum-cli export onnx` produces a model with `input_ids: [batch_size, sequence_length]` — both variable. Oracle rejects it with `ORA-54426: Tensor "input_ids" contains multiple dimensions (2) of variable size`.
     - The `oml4py` package on PyPI is a 4-file stub with no `EmbeddingModel` helper. The real `oml4py` ships with Oracle Database client, not pip.
     - The working PyPI tool is **`onnx2oracle`** (this is what `scripts/load_onnx_model.py` uses). It builds the right augmented ONNX (tokenizer + transformer + pooling + normalize).
   - **If it fails with `ORA-01031`:** step 4 was skipped or the soccer user lacks `CREATE MINING MODEL`.
   - **If it fails with `ORA-54426`:** something rewrote `load_onnx_model.py` to skip `onnx2oracle`. Don't go back to raw `optimum-cli` ONNX — it will not work.

9. **Load precomputed predictions**
   - Run: `uv run python scripts/load_predictions.py`
   - This should load roughly 2,500+ rows. Do not accept a 2-row test fixture as workshop-ready.

10. **Populate the LangChain OracleVS hybrid retrieval store**
    - Run: `uv run python scripts/load_langchain_vectors.py --reset --demo-query "Spain Brazil World Cup prediction evidence"`
    - This happens after the ML prediction table exists: it turns `PREDICCIONES_FINAL`, `VW_TEAM_STATISTICS`, and World Cup team/decade aggregates into LangChain `Document` rows in `SOCCER_LANGCHAIN_DOCS` using the `langchain-oracledb` PyPI package and the in-DB ONNX model.
    - The demo query must return at least one relevant prediction/fact document. This is the key evidence that the coding-agent build path prepared the same hybrid store Grok will use after the app starts.
    - The script attempts a vector index, a native HYBRID VECTOR INDEX, and an Oracle Text index. Hybrid-index support is image/version-sensitive; it is okay if one optional index reports `skipped` because the agent still retrieves with the best available native hybrid or Oracle Text + vector reciprocal-rank-fusion path.
    - **If it fails before inserting rows:** steps 8 or 9 were skipped, `langchain-oracledb` is missing, or the ONNX model name in `ORACLE_EMBED_MODEL` is wrong.

11. **Embed match facts into semantic memory**
    - Run: `uv run python scripts/embed_match_facts.py`
    - **Tiny dataset gotcha:** the SQL has `HAVING COUNT(*) >= 3`, so if you've only loaded a 3-row stub CSV (no real FIFA data), this inserts zero facts and reports `Inserted 0 semantic facts.` That's expected, not a failure.

12. **Optionally showcase Oracle Agent Memory SDK**
    - Run: `uv run python scripts/showcase_oracle_agent_memory.py`
    - This demonstrates the `oracleagentmemory` PyPI package in the same database with user/agent/thread-scoped durable memory. If the alpha SDK changes its API, surface the error but do not block the core workshop; the custom memory tables remain the primary path.

13. **Run the verifier, observability check, and hybrid-vs-semantic contrast check**
    - Run: `uv run python scripts/verify.py`
    - All checks must be green. A red on `PREDICCIONES_FINAL` means the real prediction parquet was not prepared or loaded; re-run steps 6 and 9. A red on `SOCCER_LANGCHAIN_DOCS` means step 10 did not populate the hybrid retrieval store. A red on `langgraph-oracledb OracleStore observability setup` means step 7 did not initialize the LangGraph OracleDB store.
    - Run the direct showcase pair:
      - `uv run python .claude/skills/soccer-agent-toolbelt/tools/run_tool.py hybrid_retrieve '{"query":"Spain Brazil World Cup prediction evidence","limit":3}'`
      - `uv run python .claude/skills/soccer-agent-toolbelt/tools/run_tool.py vector_search '{"query":"Spain Brazil World Cup prediction evidence","limit":3}'`
    - Explain the expected difference: `hybrid_retrieve` returns LangChain OracleVS documents and can surface cached ML prediction rows with `retrieval_mode`; `vector_search` returns semantic-only facts from `semantic_memory`.
    - Run: `uv run python scripts/smoke_test.py`. In addition to a real `predict_match` call, this must print LangGraph OracleDB observability events including `turn_start`, `tool_call`, `tool_result`, and `final_response`.

14. **Build and polish the React front-end with the `taste-skill`** (automatic for every attendee — do not skip unless `--skip-ui-polish` was passed)
    - The workshop now ships a premium **Vite + React + Tailwind + Framer Motion** front-end under `frontend/`. FastAPI serves the built `frontend/dist/` if it exists, and falls back to the bundled `soccer_agent/api/static/index.html` otherwise.
    - **Step 1 — build the React app first** (requires **Node 18+**):
      - Run: `cd frontend && npm ci && npm run build`
      - This produces `frontend/dist/index.html` + `dist/assets/index-*.js,*.css`, which `soccer_agent/api/main.py` mounts at `/`.
      - **If Node is missing or too old:** surface it clearly (print the `node --version` you got and that Node 18+ is required) and **fall back to the committed default UI** — `main.py` automatically serves `soccer_agent/api/static/index.html` when `frontend/dist/` is absent. Do NOT fail the whole setup over a missing Node; the API still runs against the bundled static page.
    - **Step 2 — invoke the `taste-skill`** (vendored in this repo at `.claude/skills/taste-skill/`, so it is available in the repo's Claude Code session) via the `Skill` tool, then refine the React front-end source in `frontend/src/` against it (single accent, off-black base, suggestion chips, per-tool trace cards, typing skeleton, live status pill, tactile feedback, no emoji). **Rebuild after refining:** `cd frontend && npm run build`.
    - **HARD CONSTRAINTS — the UI MUST keep working against the live API. Do NOT change:**
      - The fetch contract: `POST /chat` with body `{session_id, message}` → renders `{session_id, reply, tool_trace[]}`, where each trace item is `{name, args, result}`.
      - `GET /health` → `{oracle, grok_configured}` (used to drive the status indicator).
      - `GET /observability/{sessionId}` for ordered LangGraph OracleDB step records.
      - `DELETE /memory/{sessionId}` for reset.
      - The front-end calls these via **relative paths** (`/chat`, `/predict`, `/health`, `/memory/...`), so it is port-agnostic — keep it that way (do not hardcode a host/port).
    - **Verify after building:** start the API, load `http://localhost:8000/`, send "Predict Spain vs Brazil at a neutral venue.", and confirm the probability bar renders with the `predict_match` tool trace showing `features_used: 92`. Copy the returned `session_id` and call `GET /observability/{session_id}`; it must show ordered LangGraph OracleDB step records for the turn. Then send "Use hybrid retrieval to explain the evidence for Spain vs Brazil, and contrast it with semantic-only memory." Expand the trace and confirm `hybrid_retrieve` appears or the reply cites the startup hybrid context from `SOCCER_LANGCHAIN_DOCS`; `vector_search` should appear only for the requested semantic-only contrast. Then stop the server.
    - **If it fails:** revert the front-end source (`git checkout -- frontend/src/`) and rebuild, or remove `frontend/dist/` to fall back to the committed default `soccer_agent/api/static/index.html` — a polished-but-broken UI is worse than the shipped default. The workshop must remain runnable.

15. **Done**
    - Print: "Workshop environment ready. Start the API with: `uv run uvicorn soccer_agent.api.main:app --reload` and open http://localhost:8000/"

## Flags (optional, when invoked with arguments)

- `--retrain`: Pass `--force-retrain` to `scripts/prepare_artifacts.py` in step 6.
- `--skip-embeddings`: Skip step 8 and the vector-store population in step 10. This disables the hybrid showcase; do not use it for the final workshop demo.
- `--skip-ui-polish`: Skip the taste-skill refinement of the React front-end in step 14. The React app is still built (`frontend/dist/`) so FastAPI serves it; this only skips re-applying the latest taste-skill standards to `frontend/src/`.

## Pitfalls & lessons learned (read this first if you're building on top)

### Why these are here
This workshop was built end-to-end; every item below corresponds to a failure mode that broke a real session. They are not theoretical.

### Oracle AI Database
- **`CREATE MINING MODEL` is required for `DBMS_VECTOR.LOAD_ONNX_MODEL`.** It's not implied by `CONNECT, RESOURCE`. The default workshop user gets it via `setup.sh` (step 4).
- **`DBMS_VECTOR` is already `EXECUTE` to PUBLIC on Oracle AI Database Free.** You do NOT need to grant `EXECUTE ON SYS.DBMS_VECTOR`; in fact SYSTEM cannot grant on SYS-owned objects without `GRANT ANY OBJECT PRIVILEGE`, so trying will give you `ORA-01031`.
- **`VECTOR(384, FLOAT32)` is the type to use for embeddings.** Pick the dim that matches your loaded ONNX model; the workshop uses 384 because `all-MiniLM-L6-v2` outputs 384.
- **`VECTOR_DISTANCE(a, :q, COSINE)` returns lower-is-better.** Order ascending. The query embedding (`:q`) must be passed as a Python `array.array('f', ...)` of the right length; passing a numpy ndarray directly raises a type error.
- **LangChain OracleVS table is additive and workshop-critical.** `SOCCER_LANGCHAIN_DOCS` is managed by `langchain-oracledb`; use `scripts/load_langchain_vectors.py --reset` after retraining so cached prediction documents match the latest model. The final Grok 4 chat should use this table via `hybrid_retrieve`/startup grounding for evidence, not plain semantic memory alone.
- **LangGraph OracleDB observability is per-store-instance.** `OracleStore.setup()` must be called on each fresh `OracleStore(conn)` object before `put()`/`search()` so the package initializes its internal table-name map, even after the schema tables already exist.
- **Native HYBRID VECTOR INDEX is version-sensitive.** When the database can create the hybrid index, `OracleHybridSearchRetriever` is used directly. If an image cannot create it, the workshop still showcases hybrid retrieval by fusing Oracle Text results with vector similarity in Python, while all data and indexes remain in Oracle.

### In-DB ONNX embedding models
- **Use `onnx2oracle` (PyPI).** Not `optimum-cli` directly. Not `oml4py` (PyPI stub). Not a hand-rolled `DBMS_VECTOR.LOAD_ONNX_MODEL` call against a HuggingFace export.
- **Presets (`onnx2oracle presets`):** `all-MiniLM-L6-v2` (384, ~90MB), `all-MiniLM-L12-v2` (384, ~130MB), `all-mpnet-base-v2` (768, ~420MB), `bge-small-en-v1.5` (384, ~130MB), `nomic-embed-text-v1` (768, ~540MB).
- **The Oracle model name is uppercase with underscores** (e.g. `ALL_MINILM_L6_V2`). It is NOT the HuggingFace repo path.

### python-oracledb (3.x) sharp edges
- **`IS JSON` CLOBs auto-decode to Python dict/list.** If you wrote `json.loads(value)` you'll get `TypeError: the JSON object must be str, bytes or bytearray, not dict`. Guard with `isinstance(val, (str, bytes, bytearray))`.
- **LOB locators die after connection close.** If you build dataclasses inside a list comprehension AFTER the `with get_connection()` block exits, `.read()` on any returned CLOB raises `DPY-1001: not connected to database`. Fix: materialize all CLOBs (`val.read() if hasattr(val, 'read') else val`) INSIDE the `with` block.
- **Pass float32 vectors as `array.array('f', list)`.** numpy ndarrays don't bind to `VECTOR` columns directly.
- **`load_dotenv()` with no args needs a stack frame.** If you pipe Python to stdin (`uv run python - <<EOF`), `find_dotenv()` raises `AssertionError`. Pass an explicit path: `load_dotenv(Path.cwd() / ".env")`.

### OCI Generative AI Inference
- **The `sk-...` bearer key authenticates against the *inference* endpoint only**, not the *control plane*. You can call `/20231130/actions/chat` and `/actions/embedText`, but you can't `LIST` models with that key. To learn what model IDs are valid, look in the OCI Console under Generative AI → Models.
- **Compartment OCID is required in the request body** (under `servingMode.compartmentId`), even though authentication is by bearer key. Both must be set.
- **Tool calling is NOT exposed through this endpoint with the bearer key.** Including a `tools` array (in either GENERIC or COHERE apiFormat, with or without the OpenAI-style `{"type":"FUNCTION","function":{...}}` wrapper) returns `400: Please pass in correct format of request.` on every model we tested — `xai.grok-4`, `xai.grok-3`, `cohere.command-r-plus-08-2024`. The agent loop works around this with a prompt protocol (see next item).
- **Prompt-protocol tool calling pattern:** append tool schemas to the system message, instruct the model to emit a single JSON object `{"tool": "...", "args": {...}}` when it wants to call one, and parse JSON tool calls out of the response text. See `soccer_agent/agent/grok_client.py` for the working implementation.
- **`role: "tool"` messages get rejected without `toolCallId`.** Since we never receive a `toolCallId` (tool calling isn't native), surface tool results back to the model as `role: "system"` messages instead. Also: skip persisted `role: "tool"` turns when rebuilding the message list for the next iteration.

### Container networking
- **Bind Oracle to `127.0.0.1:1525:1521`**, not `0.0.0.0`. The workshop image's `system` password is well-known; never expose port 1521/1525 to a public interface.
- **Healthcheck must use a sentinel value, not `1`.** Searching for `1` in sqlplus output matches the release banner (`Release 23.x.x`) and connection failures (`ORA-01017`), giving false positives. Use `SELECT 424242` and `grep -Eq '^[[:space:]]*424242[[:space:]]*$'`.
