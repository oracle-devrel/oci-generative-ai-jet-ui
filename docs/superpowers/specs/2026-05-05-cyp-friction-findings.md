# choose-your-path friction findings — 2026-05-05

Consolidated from 4 friction-pass runs walking the live skill set against Oracle 26ai Free + OCI Grok 4. Each run's raw friction file lives at `choose-your-path/tests/<run-name>/_friction.md` (gitignored) — those are authoritative for the cited "what" / "where" / "expected" details. This document is the **deduped action list** for the skill edits in commit `fix(choose-your-path): apply friction findings`.

| Run | Verify | Findings logged | Memory persists |
|---|---|---|---|
| beginner-pdfs | OK (db, vector, inference) | 13 | n/a |
| intermediate-nl2sql | OK (db, vector, inference, mcp) | 12 | n/a |
| advanced-hybrid-analyst | OK (db, vector, inference, mcp, memory, no_forbidden_imports) | 14 | n/a |
| advanced-self-mem | OK (db, vector, inference, mcp, memory, no_forbidden_imports) | 15 | **yes** |

**Total raw findings: 54.** Unique actionable findings after dedup: **22**, ordered by severity.

---

## P0 — must fix; the skill claims things that don't actually work

### P0-1 — `oracle-database-mcp-server` is not on PyPI
- **Surfaced in:** runs #2, #3, #4 (3 of 4 runs)
- **Where:** `choose-your-path/skills/oracle-mcp-server-helper/SKILL.md` step 2 (`pip install oracle-database-mcp-server` fails); `choose-your-path/intermediate/SKILL.md` step 3a-6 + `advanced/SKILL.md` step 3a-6 (both invoke the helper).
- **What:** The package name does not resolve on PyPI. The helper skill cannot be followed as written.
- **Edit:** Replace the helper's "install" step with a **scaffolded local-tool implementation** that wraps `oracledb.Cursor` directly via four `langchain_core.tools.BaseTool` subclasses (`list_tables`, `describe_table`, `run_sql`, `vector_search`). Same surface to the agent; no missing dependency. Cite working pattern at `choose-your-path/tests/advanced-hybrid-analyst/src/hybrid_analyst/mcp_client.py`.

### P0-2 — `oci-openai` shim is broken against current `openai>=1.x`
- **Surfaced in:** runs #1, #2, #3, #4 (all four).
- **Where:** `choose-your-path/shared/snippets/oci_chat_factory.py` (the load-bearing chat factory); `shared/references/oci-genai-openai.md`; deps lists in beginner / intermediate / advanced `pyproject.toml` examples.
- **What:** `client.chat.completions.create(...)` raises `APIConnectionError → AttributeError: 'URL' object has no attribute 'decode'` because `oci-openai` passes `httpx.URL` where `urllib.parse._decode_args` expects a string. The OpenAI-compat path is not stable across SDK versions.
- **Edit:** Rewrite the snippet to use **`oci.generative_ai_inference.GenerativeAiInferenceClient`** directly with `GenericChatRequest` + `OnDemandServingMode`. Drop `oci-openai` (and `openai` if not used elsewhere) from the per-tier deps. Add a "stack-note" section in `oci-genai-openai.md` explaining the OpenAI-compat path is unstable and the canonical recipe is the direct OCI SDK. The model id is `xai.grok-4` (not `grok-4`) — encode in the snippet.

### P0-3 — `OracleVS` JSON metadata column requires app-tablespace; SYSTEM connection fails ORA-43853
- **Surfaced in:** runs #1, #2, #3, #4 (all four).
- **Where:** `choose-your-path/skills/oracle-aidb-docker-setup/SKILL.md` step 3 + step 4 (writes `.env` with `DB_USER=SYSTEM`); `langchain-oracledb-helper/SKILL.md` step 4.
- **What:** SYSTEM tablespace lacks ASSM. `OracleVS.from_texts` fails: `ORA-43853: JSON type cannot be used in non-automatic segment space management tablespace "SYSTEM"`.
- **Edit:** Extend the docker-setup skill with a **Step 6** that creates an app user (default `<package_slug_upper>`, override-able via `app_user` input) with `DEFAULT TABLESPACE USERS QUOTA UNLIMITED ON USERS` and grants `CONNECT, RESOURCE, CREATE SESSION, CREATE TABLE, CREATE VIEW, CREATE PROCEDURE, CREATE MINING MODEL`. Update the written `.env` so `DB_USER=<app_user>`, with `SYS_PASSWORD=<sys-pwd>` available separately for SYSDBA-only operations. Update `shared/references/oracle-26ai-free-docker.md` accordingly.

### P0-4 — In-DB ONNX scaffold is brittle; `onnx2oracle` does it cleanly in one command
- **Surfaced in:** runs #2, #3, #4 (the in-DB tiers).
- **Where:** `choose-your-path/intermediate/SKILL.md` step 3a-4; `advanced/SKILL.md` step 3a-4; `shared/references/onnx-in-db-embeddings.md`.
- **What:** The skill hand-rolls a 3-step pipeline (`optimum.onnxruntime` export → `onnxruntime_extensions` BertTokenizer wrap → `LOAD_ONNX_MODEL` SQL). The reference doc itself calls the BertTokenizer wrap "the gnarly part." Meanwhile, [`github.com/jasperan/onnx2oracle`](https://github.com/jasperan/onnx2oracle) ships as a one-command CLI on PyPI: `pip install onnx2oracle && onnx2oracle load sentence-transformers/all-MiniLM-L6-v2 --name MY_MINILM_V1 --dsn 'USER/PWD@host:port/service' --force`.
- **Edit:** Make `onnx2oracle` the **default** in intermediate / advanced. Replace step 3a-4's hand-rolled scripts with `pip install onnx2oracle` + the CLI invocation. Keep the manual export as an **appendix** in `shared/references/onnx-in-db-embeddings.md` for users who can't add the dep. Required GRANTs (per finding P0-5) live alongside.

### P0-5 — Required GRANTs for in-DB ONNX are missing from the skill
- **Surfaced in:** runs #2, #3, #4.
- **Where:** `choose-your-path/skills/oracle-aidb-docker-setup/SKILL.md` (the user-creation step we're adding in P0-3); `intermediate/SKILL.md` step 3a-4; `advanced/SKILL.md` step 3a-4.
- **What:** `LOAD_ONNX_MODEL` and `VECTOR_EMBEDDING(MODEL ...)` need `CREATE MINING MODEL` (in the app user) and `EXECUTE ON SYS.DBMS_VECTOR` (granted from SYSDBA). Currently undocumented; users hit `ORA-29516` or similar.
- **Edit:** In docker-setup's new app-user creation block, include both grants. The `EXECUTE ON SYS.DBMS_VECTOR` step requires `SYSDBA` — connect as `SYS AS SYSDBA` for that single GRANT and document why. Keep the rest of the user creation as the regular DBA the skill already uses.

### P0-6 — `advanced/SKILL.md` idea 2 references `web_fetch` tool with no implementation
- **Surfaced in:** run #4.
- **Where:** `choose-your-path/advanced/SKILL.md` step 3b "Idea 2 — Self-improving research agent" (mentions `src/<package_slug>/tools/web_fetch.py` but does not specify what it does or its scope).
- **What:** Idea 2 is unbuildable as written — the agent's research task needs an outbound HTTP tool with retry / fetch-and-extract logic that the skill never specifies.
- **Edit:** Add `choose-your-path/shared/snippets/web_fetch_tool.py` shipping a `httpx.get` + `trafilatura.extract` LangChain BaseTool with a `(url, fallback_query)` signature: try the URL, if it 4xx/5xx or times out, the agent's `fallback_query` triggers an in-corpus search instead. Cite this in `advanced/SKILL.md` step 3b idea 2 as the canonical implementation. This was the substance of run #4's "scope A vs scope B" choice.

---

## P1 — should fix; works once you know but trips every new user

### P1-1 — `DistanceStrategy` import path: `langchain_oracledb.utils.distance_strategy` does not exist
- **Surfaced in:** runs #1, #2, #3, #4.
- **Where:** `choose-your-path/skills/langchain-oracledb-helper/SKILL.md` step 4 (the `store.py` skeleton imports it from `langchain_oracledb.utils.distance_strategy`); same import in `shared/templates/verify.template.py`.
- **What:** `langchain-oracledb==1.3.0` does not export `DistanceStrategy`. Actual location: `langchain_community.vectorstores.utils.DistanceStrategy`.
- **Edit:** Replace import in helper SKILL's example and in the verify template with `from langchain_community.vectorstores.utils import DistanceStrategy`. Add `langchain-community>=0.3` to the helper's required deps (already transitively pulled, but should be explicit). Add a one-line note in `shared/references/langchain-oracledb.md` explaining the package layout.

### P1-2 — `langchain-oracledb-helper` claims to ship `InDBEmbeddings` but doesn't
- **Surfaced in:** runs #2, #3, #4.
- **Where:** `choose-your-path/skills/langchain-oracledb-helper/SKILL.md` step 2 + step 4 ("the helper writes the `InDBEmbeddings` subclass"); `intermediate/SKILL.md:74` references the same.
- **What:** The shared/snippets directory has no `in_db_embeddings.py`. The helper's instructions assume a class that doesn't exist, and the user has to write it — which is exactly the boilerplate the helper is supposed to remove.
- **Edit:** Add `choose-your-path/shared/snippets/in_db_embeddings.py` with a working `Embeddings` subclass calling `VECTOR_EMBEDDING(MODEL_NAME USING :t AS data) FROM dual` via `oracledb.Cursor`. Update the helper SKILL step 4 to copy this snippet verbatim into `store.py` when `embedder=in-db-onnx`. Cite working pattern at `choose-your-path/tests/advanced-hybrid-analyst/src/hybrid_analyst/store.py` (which agents implemented from scratch in this pass).

### P1-3 — `OracleChatHistory` snippet broken with `oracledb 4.x` JSON column
- **Surfaced in:** runs #3, #4.
- **Where:** `choose-your-path/shared/snippets/oracle_chat_history.py`.
- **What:** Under `oracledb 4.x`, the snippet's payload encoding doesn't round-trip cleanly through the JSON column type. Run #3's `history.py` has the working dict-payload approach; run #4 reused it.
- **Edit:** Update `shared/snippets/oracle_chat_history.py` to use `json.dumps(payload).encode()` on insert and `json.loads(row[0].read())` on select (CLOB read). Cite the working version at `choose-your-path/tests/advanced-hybrid-analyst/src/hybrid_analyst/history.py`.

### P1-4 — `verify.py` "FAIL" label names the previous successful step, not the failing one
- **Surfaced in:** run #1 (after a 10-minute wild-goose chase).
- **Where:** `choose-your-path/shared/templates/verify.template.py` `main()`.
- **What:** When `check_inference()` fails, the printed line is `verify: FAIL (vector): APIConnectionError ...` because `last = checks[-1]` resolves to "vector" (last successful) instead of "inference" (failing).
- **Edit:** Restructure `main()` so each `check_*()` call records its own step name BEFORE invocation (`step = "inference"; check_inference()`), so the except block prints the actual failing step.

### P1-5 — `chat_history` migration uses non-Oracle SQL idiom
- **Surfaced in:** run #1.
- **Where:** `choose-your-path/skills/langchain-oracledb-helper/SKILL.md` step 5 (the `migrations/001_chat_history.sql` example uses `CREATE TABLE IF NOT EXISTS`).
- **What:** Oracle does not support `IF NOT EXISTS` on `CREATE TABLE`. Migration fails. Run #1's working version wraps DDL in a PL/SQL anonymous block that swallows ORA-00955.
- **Edit:** Replace the helper's example migration with the working idempotent PL/SQL block from `tests/beginner-pdfs/migrations/001_chat_history.sql`.

### P1-6 — env-var naming inconsistent across skills
- **Surfaced in:** runs #1, #2, #3, #4.
- **Where:** `oracle-aidb-docker-setup/SKILL.md` (writes `DB_USER` / `DB_PASSWORD` / `DB_DSN`); `shared/templates/verify.template.py` (reads `ORACLE_USER` / `ORACLE_PASSWORD` / `ORACLE_DSN`).
- **What:** Project's `.env` after running docker-setup uses `DB_*` names, but the verify template reads `ORACLE_*`. Verify always fails on a fresh project until the user adds duplicate keys. Run #1's `.env` shows both sets of vars set to identical values — the workaround.
- **Edit:** Pick one naming convention. Recommend `DB_*` (matches the helper's `store.py` skeleton). Update verify template to read `DB_*`. Update `shared/references/oracledb-python.md` to use `DB_*` consistently.

### P1-7 — docker-compose template hard-codes ports / volume; skill claims `port` input works
- **Surfaced in:** runs #1, #3 (parallel-run isolation requirement).
- **Where:** `choose-your-path/shared/templates/docker-compose.oracle-free.yml` lines 21-23 (`"1521:1521"`) and 28 (`oracle-data:/opt/oracle/oradata`); `oracle-aidb-docker-setup/SKILL.md` step 3 (claims placeholders `${ORACLE_PORT}` etc are "left in").
- **What:** Template is hard-coded; placeholders aren't actually used. Two parallel runs collide on port 1521.
- **Edit:** Update template to use `"127.0.0.1:${ORACLE_PORT}:1521"` and `${ORACLE_VOLUME}:/opt/oracle/oradata`. Add `port_offset` input to the docker-setup skill (advanced tier needs this for parallel demos).

### P1-8 — `BaseTool.invoke` cannot be patched on instance under Pydantic 2
- **Surfaced in:** run #2.
- **Where:** `choose-your-path/skills/oracle-mcp-server-helper/SKILL.md` (the SQLcl-tee monkeypatch approach implied if you fold the tee in per the next finding).
- **What:** `tool.invoke = wrapper` raises `pydantic_core._pydantic_core.ValidationError`. Tools must be subclassed.
- **Edit:** In the helper SKILL (and any docs that show "wrap the run_sql tool"), replace monkeypatch examples with a `class TeedRunSQL(BaseTool)` subclass that overrides `_run`. Cite working pattern at `tests/intermediate-nl2sql/src/nl2sql/tool_registry.py`.

### P1-9 — Agent loop: max-step exhaustion without `finish` leaves placeholder content
- **Surfaced in:** run #4.
- **Where:** `choose-your-path/advanced/SKILL.md` step 3b idea 2 ("planner-executor loop").
- **What:** Without explicit "finish substantively after 2-3 useful tool calls" guidance and `MAX_STEPS` headroom, the agent hits cap and the persisted memory holds placeholder content. Run #4 had to rewrite the system prompt and bump `MAX_STEPS` from 8 to 12.
- **Edit:** Update the planner-executor skeleton in `advanced/SKILL.md` step 3b to include the working prompt rules: tool args are JSON objects (not lists), `run_sql` rejects mutating SQL in read_only mode, memory writes are automatic at `finish`, and the loop must `finish` after 2-3 useful tool calls. `MAX_STEPS` defaults to 12.

---

## P2 — nice to fix; doesn't block but adds drag

### P2-1 — `conda-forge python=3.12` doesn't include pip
- **Surfaced in:** run #1.
- **Edit:** Add a "Conda alternative" bullet in beginner / intermediate / advanced step "create venv": `conda create -n <env> -c conda-forge --override-channels python=3.12 pip -y`. Note that `pip` MUST be listed.

### P2-2 — `conda activate` doesn't work in non-interactive bash
- **Surfaced in:** all four runs.
- **Edit:** Replace `conda activate <env> && pip install ...` patterns in the skill set with `~/miniconda3/envs/<env>/bin/pip install ...` (absolute path). Add a one-line note explaining why.

### P2-3 — Docker group membership requires fresh shell
- **Surfaced in:** runs #1, #2, #3, #4.
- **Edit:** Add a one-line note to `oracle-aidb-docker-setup/SKILL.md` Step 0: "After installing Docker, you must open a fresh shell for `docker` group membership to take effect — or use `sudo docker` for the rest of this session."

### P2-4 — `env.example` template still pitches Ollama as beginner default
- **Surfaced in:** run #1.
- **Where:** `shared/templates/env.example` lines 13-29.
- **Edit:** Re-label Ollama (Path A) as "(archived; see `archive/beginner-ideas.md`)". Make OCI (Path B) the active default at all tiers per the post-restructure design.

### P2-5 — `onnx2oracle` CLI argument shape doesn't match the friction-pass instructions
- **Surfaced in:** run #3.
- **Edit:** When citing `onnx2oracle` in intermediate / advanced step 3a-4, use the actual CLI: `onnx2oracle load <hf_model> --name <DB_MODEL_NAME> --dsn 'USER/PWD@host:port/service' --force`. The `--user` and `--password` flags are not separate.

### P2-6 — `vector_search` MCP tool surface needs collection arg, undocumented
- **Surfaced in:** run #3.
- **Edit:** When `vector_search` is enumerated in `oracle-mcp-server-helper/SKILL.md` Step 4 / 5, show the BaseTool's `args_schema` explicitly — it takes `collection: str` and `query: str` (and optional `k`, default 5). Otherwise the agent doesn't know what to pass.

### P2-7 — Memory cleanup not documented for advanced idea 2
- **Surfaced in:** run #4.
- **Edit:** Add a "Resetting memory" subsection to `advanced/SKILL.md` idea 2 (TRUNCATE the four memory tables; show the SQL).

### P2-8 — Summary truncation mid-word leaks into agent quotes
- **Surfaced in:** run #4.
- **Edit:** Update the summary-write helper in `shared/snippets` (or scaffold one if missing) to chunk on word boundaries before embedding so agents can't quote mid-word artefacts back at users.

### P2-9 — `sqlplus` vs `sql` (SQLcl) naming confusion
- **Surfaced in:** run #2.
- **Edit:** Be explicit in docker-setup SKILL: the healthcheck uses `sqlplus` (inside the container); user-facing scripts use `sql` (SQLcl on the host).

### P2-10 — Notebook deferral: should it be a Bar B requirement?
- **Surfaced in:** runs #2, #3, #4 (meta).
- **Decision needed:** Today the SKILLs say notebook is "default yes" at intermediate, "mandatory" at advanced — but the friction-pass treated it as optional and most runs deferred it without breaking Bar B. **Recommendation: keep mandatory at advanced, default-yes at intermediate, but explicitly note in the SKILL that the notebook is for users (the demo payoff) — the friction-pass agents skipped it because the orchestrator's verify+chat evidence is sufficient for a *test* but not for a *user demo*.**

---

## P3 — observations only, no edit

### P3-1 — `ORDER BY 1` over a CLOB column raises ORA-22848
- Surfaced in run #4 dev workflow. Worth a one-line gotcha note in `shared/references/oracledb-python.md`.

### P3-2 — Router gracefully handles user's "Q3 vs Q4" slip
- Surfaced in run #3. Positive observation; no action.

---

## SQLcl tee decision (consolidation question)

Run #2's `README_SQLCL.md` recommended **fold into the intermediate skill**. Reasons captured there:
- ~50 lines of code; latency cost is zero (background `subprocess.Popen`).
- Teaching value: MCP shows the SQL the *agent* emits, SQLcl shows what the *DB* actually did.
- Pairs naturally with the existing `[sqlcl_log: ...]` token in the streamed response.

**Decision:** **fold in as default**. Edit:
- `intermediate/SKILL.md` step 3c: scaffold `sql/`, `logs/`, and the SQLcl tee wrapping in the `tool_registry.py` step.
- Add `shared/references/sqlcl-tee.md` documenting install (Ubuntu zip from `https://download.oracle.com/otn_software/java/sqldeveloper/sqlcl-latest.zip` + `default-jre-headless`) and how to inspect logs.
- `shared/snippets/sqlcl_tee.py` — copy from `tests/intermediate-nl2sql/src/nl2sql/sqlcl_tee.py`.

---

## Pre-existing findings from spec — resolution

- **Pre-1 — beginner SKILL.md:124 `dim == 1024`** → applied as part of P0/P1 sweep (one-line fix to `384`).
- **Pre-2 — intermediate SKILL.md:74 `InDBEmbeddings` reference** → resolved by P1-2 (helper now actually ships the snippet).

---

## Runs blocked

None. All 4 runs hit Bar B.

---

## Findings deferred to a follow-up pass

- P3-1 (ORA-22848 dev gotcha note).
- "Notebook as Bar B" decision (P2-10) — recommendation captured; final decision is the skill maintainer's.
