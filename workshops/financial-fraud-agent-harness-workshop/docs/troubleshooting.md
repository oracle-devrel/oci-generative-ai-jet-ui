# Troubleshooting Guide

This guide covers the most common issues encountered during the Financial Data Agent Workshop and how to resolve them.

---

## Oracle Database Issues

### ORA-51962: The vector memory area is out of space

**Symptom:** Creating a vector index (`CREATE VECTOR INDEX ... ORGANIZATION INMEMORY ...`) raises `ORA-51962`.

**Cause:** `vector_memory_size` is `0` in the running Oracle instance. HNSW vector indexes live in a dedicated SGA pool that defaults to off on the Free image.

**Fix (two-step — bounce required):**

```python
import oracledb
conn = oracledb.connect(user="sys", password="OraclePwd_2025",
                        dsn="localhost:1521/FREEPDB1",
                        mode=oracledb.AUTH_MODE_SYSDBA)
conn.cursor().execute("ALTER SYSTEM SET vector_memory_size = 512M SCOPE=SPFILE CONTAINER=ALL")
conn.commit(); conn.close()
```

Then bounce the database:

```bash
docker restart oracle-free
```

Wait ~60 seconds for FREEPDB1 to report `READ WRITE`, restart the Jupyter kernel, and re-run from §1.

---

### ORA-04036: PGA memory used by the instance exceeds PGA_AGGREGATE_LIMIT

**Symptom:** the cross-encoder rerank (`PREDICTION(RERANKER_ONNX USING :q AS DATA1, doc AS DATA2)`) falls back to plain cosine ordering after `ORA-04036`.

**Cause:** The Free image ships with `pga_aggregate_limit = 2G`, which is too tight for the reranker's transient PGA use.

**Fix:** Raise it at the CDB level (PDBs can't change this parameter):

```bash
docker exec -i oracle-free sqlplus -s / as sysdba <<'SQL'
ALTER SESSION SET CONTAINER = CDB$ROOT;
ALTER SYSTEM SET pga_aggregate_limit = 4G SCOPE=BOTH;
EXIT
SQL
```

`SCOPE=BOTH` means the change applies live and persists across restarts. No bounce needed.

---

### ORA-12541 / Connection refused

**Symptom:** Any database connection attempt fails with `Connection refused` or `DPY-6005`.

**Cause:** The Oracle container isn't running.

**Fix:**

```bash
docker ps
```

If `oracle-free` isn't listed, run the idempotent provisioner (it starts the container and waits until it is healthy):

```bash
bash .devcontainer/provision.sh
```

Then retry the connection cell.

---

### ORA-01017: Invalid username or password

**Symptom:** Connecting as `AGENT` fails with an authentication error.

**Cause:** `AGENT` doesn't exist yet (provisioning did not finish), or the container was rebuilt with a stale volume.

**Fix:** Re-run provisioning (it creates `AGENT` if missing and resets the `SYS` password to the workshop default):

```bash
bash .devcontainer/provision.sh
```

---

### Oracle container starts but never becomes ready

**Symptom:** `docker ps` shows `oracle-free` running, but the connection cell still fails.

**Cause:** Oracle's listener takes a few seconds longer than the container healthcheck signals.

**Fix:** Check the logs:

```bash
docker logs oracle-free 2>&1 | tail -20
```

If you see `DATABASE IS READY TO USE!`, Oracle is up. The pre-built `connect()` helper retries automatically; if it's still failing after 5 attempts, restart the kernel and try again.

---

## Codespace and Environment Issues

### Codespace shows "Setting up your Codespace" for more than 10 minutes

**Symptom:** The Codespace is stuck on the loading screen.

**Cause:** First-time Oracle Free image initialisation can take 3-5 minutes. After that, `postCreateCommand` runs the build script.

**Fix:** This is expected. Do not refresh. Wait for the terminal prompt. If it exceeds 10 minutes:

```bash
docker logs oracle-free 2>&1 | tail -20
```

---

### `OPENAI_API_KEY` / `OCI_GENAI_API_KEY` is None

**Symptom:** A cell fails because `os.environ.get(...)` returns `None`.

**Cause:** The Codespaces secret was added after this Codespace was created, so it wasn't injected at startup. (Secrets are only injected at creation time.)

**Fix:** Set the key manually for this session only:

```python
import os
os.environ["OPENAI_API_KEY"] = "sk-..."     # or
os.environ["OCI_GENAI_API_KEY"] = "..."
```

Do not commit this to git. For permanent fixes, stop the Codespace, add the secret in repo settings, and create a new one.

---

### Slow answers or 429s during a busy session (instructor)

Grok-4.3 limits are per tenancy per region, so rotating keys cannot help. The router in `oci_key_rotation.py` instead falls back silently: `grok-phx` → `grok-chi` (Chicago keys) → `gptoss-chi` (`openai.gpt-oss-120b`). A rate-limited lane cools for `OCI_GENAI_FALLBACK_COOLDOWN_S` seconds (default 120), then calls return to it. Attendees see nothing; inspect what happened with `tail ~/.cache/fraud-workshop/llm-router.log` (override with `OCI_GENAI_ROUTER_LOG`; the app also prints `[llm-router] ...` lines). If the fallback secrets (`OCI_GENAI_FALLBACK_ENDPOINT`, `OCI_GENAI_FALLBACK_API_KEY..6`) are missing, only the Phoenix lane runs.

---

### Jupyter kernel "Python 3.11" not found

**Symptom:** The notebook asks you to select a kernel and Python 3.11 isn't listed.

**Fix:**

```bash
pip install -q ipykernel && python -m ipykernel install --user --name python3 --display-name "Python 3.11"
```

Reload the VS Code window (`Cmd/Ctrl + Shift + P` → `Developer: Reload Window`) and select the kernel again.

---

### `Run All` stops at the first TODO (red cell)

**Symptom:** You run the whole notebook and it halts early with a red cell, usually `TODO 1` or a `NotImplementedError`.

**Cause:** That is the workshop. The seven TODO stubs raise on purpose and every TODO has a hard-stop assert below it, so you cannot barrel forward with a half-built harness.

**Fix:** Work top to bottom and implement each TODO in place; or open `notebook_complete.ipynb`, which is the same notebook with all eight solved. Nothing is broken and no state is corrupted by stopping there.

---

### An import fails: `oracledb` / `numpy` / `openai` / `oracleagentmemory`

**Symptom:** `ModuleNotFoundError` in the first code cells.

**Cause:** VS Code picked a different Python interpreter than the workshop one.

**Fix:** Command Palette → **Notebook: Select Notebook Kernel** → **Python 3.11** (`/usr/local/bin/python`). The dependencies are pre-installed for that interpreter — do not `pip install`. See `images/select_kernel.png`.

---

### `§1.2` preflight is red

**Symptom:** The preflight table prints one or more ❌ rows.

**Cause / Fix:** Each red row prints its own remedy:

- *FINANCE tables / transactions / SAR reports* → the seed did not finish: `cd app && python scripts/bootstrap.py && python scripts/seed.py`.
- *ONNX embedder missing* → `cd app && python scripts/bootstrap.py` (needs the `vector_memory_size` pool from the same script).
- *chat LLM: 0 lane(s)* → no OCI GenAI key reached the kernel's environment; add it as a Codespaces secret (then restart), or re-run §1.1 and paste the key at its prompt. (`app/.env` feeds the app, not the notebook kernel.)
- *Oracle Text index absent* → informational: §3.1 creates it before the keyword leg needs it.

The cell hard-fails only on a seeded `FINANCE` and a present embedder, because every later block depends on those two.

---

### Part 6 (`Autonomous AML triage`) issues

**Symptom:** `0 alert(s)` in the queue, `REVIEW_REQUIRED` rows, or every alert failing with a stub error.

**Fix:** See the troubleshooting section of [Part 6: Autonomous AML triage](part-6-autonomous-aml-triage.md#troubleshooting). The short version: `0 alerts` means the watermark already covers the window (`IGNORE_WATERMARK = True` re-triages it); `REVIEW_REQUIRED` is the intended fallback when a model reply does not validate; a stub error means a TODO above is still unimplemented.

---

## OAMP / Memory Issues

### `ValueError: user already exists` (or agent already exists)

**Symptom:** A cell that calls `memory_client.add_user(...)` or `memory_client.add_agent(...)` raises `ValueError: user already exists`.

**Cause:** The user/agent was registered on a prior run; OAMP rejects duplicates.

**Fix:** Wrap the calls in `try/except ValueError` and check for `"already exists"` in the message — see the [Part 2 guide](part-2-oamp-memory.md).

---

### Scanner returns 0 facts

**Symptom:** `run_scan(agent_conn, owner=DEMO_USER)` reports `facts_total = 0`.

**Cause:** The `owner` argument is case-sensitive at the SQL layer (`ALL_TABLES.owner` is always uppercase). Or the FINANCE seed cell didn't complete.

**Fix:** Confirm the user exists and has tables:

```python
with sys_conn.cursor() as cur:
    cur.execute("SELECT COUNT(*) FROM all_tables WHERE owner = 'FINANCE'")
    print("table count:", cur.fetchone()[0])
```

Should print `15` (the seed's tables; spatial-index helper tables and anything you create yourself add to it). If `0`, run `bash .devcontainer/provision.sh`.

---

### `retrieve_knowledge` returns no results

**Symptom:** Calling `retrieve_knowledge` after a successful scan returns an empty list.

**Cause:** The ONNX embedder didn't register, or the `kinds=` filter is too restrictive.

**Fix:** Check the embedder is loaded:

```python
with agent_conn.cursor() as cur:
    cur.execute("SELECT model_name FROM user_mining_models")
    print(list(cur))
```

Should include `ALL_MINILM_L12_V2`. If empty, the embedder was never loaded — run `bash .devcontainer/provision.sh` (or `cd app && python scripts/bootstrap.py`).

For `kinds=`, try without a filter first to confirm there are memories at all:

```python
retrieve_knowledge("table", k=5)  # no kinds filter
```

---

## Tool Issues

### `ValueError: tool 'foo' has no docstring`

**Symptom:** `@register` raises this error.

**Cause:** The `_build_schema` helper requires a non-empty docstring — it's the tool's public spec, embedded for retrieval.

**Fix:** Add a docstring describing what the tool does and *when* to call it. "Use this when..." is good phrasing.

---

### `openai.BadRequestError: 400 ... messages with role 'tool' must be a response to a preceding message with 'tool_calls'`

**Symptom:** The agent loop raises this on the second LLM call.

**Cause:** You appended a `tool` message to `messages` without first appending the assistant's `tool_calls` message.

**Fix:** Make sure the loop body is in this order:

1. `msg = chat(messages, tools=tool_schemas).choices[0].message`
2. **Append `assistant_message(msg)`** to `messages`
3. For each `tc` in `msg.tool_calls`, append a `tool` message with `tool_call_id=tc.id` (`call_tool` runs it)

See [§5.3 in the Part 5 guide](part-5-agent-loop.md#todo-8-agent_turn) for the exact pattern.

---

### Agent calls the same tool with the same args repeatedly

**Symptom:** The trace shows the same `(tool, args)` over and over until budget exhaustion.

**Cause:** GPT-class models occasionally loop on a tool when the result is empty or unhelpful.

**Fix:** The complete-notebook version of `agent_turn` adds a 3-deep dedupe — short-circuiting identical dispatches. For the workshop demo, keep `max_iterations` low (≤ 8) and let the budget catch it.

---

## Identity and Deep Data Security

### `ORA-00901: invalid CREATE command` when installing identity rules

Expected on the workshop image, not a bug. `CREATE DATA ROLE`, `CREATE END USER`, and `CREATE DATA GRANT` are **Deep Data Security**, an Enterprise-class 26ai feature, and the Codespace runs **26ai Free**. `setup_deep_security.py` probes for this (`DBMS_DEEP_SEC` and the data-grant views) and installs the `DBMS_RLS` (VPD) backend instead — same rule set, same JSON output.

See what your instance actually supports:

```bash
cd app && python scripts/setup_deep_security.py --ddl-only
```

The probe report at the top prints the backend it chose, and the Deep Sec DDL is written to `app/scripts/out/deep_sec_ddl.sql` without touching the database.

### A persona still sees every region

The VPD backend is **fail-open**: with no end-user context set, `SYS_CONTEXT('EDA_CTX','END_USER')` is `NULL` and every policy predicate evaluates to `1=1`.

First check that the rules are installed:

```bash
cd app && python scripts/setup_deep_security.py --demo
```

If that table filters correctly but the app does not, the rule set is fine and the app is not driving it. Both read paths — `agent/tools.py::tool_run_sql` and `api/data_routes.py` — must set the context **before** executing. Confirm the policies exist:

```sql
SELECT object_name, policy_name FROM all_policies WHERE object_owner = 'FINANCE';
```

Fifteen policies is the canonical set.

### `ORA-28113: policy predicate has error`

A predicate is subquerying a table that carries a policy of its own. `FINANCE.branches` is policied, so a policy on `FINANCE.accounts` that reads `FINANCE.branches` fails at query time. That is why the scope predicate reads the precomputed `AGENT.agent_scope` table instead. Re-run `python scripts/setup_deep_security.py` to rebuild the rule tables and the predicates together.

### `ORA-23607: invalid column` from a mask

The mask registry names a column that does not exist. This is the failure mode the [Deep Data Security reference](reference/deep-data-security.md) is built around: in Python a wrong column name is a silent no-op, while the kernel rejects it immediately. Check the persona masks in `api/identities.py` against the real schema.

### `NameError: name 'CURRENT_END_USER' is not defined`

That name belongs to the long-form reference build. Here the identity boundary is
`AGENT.SET_EDA_CTX` (set directly, or through the app's `db/deep_security.py::set_identity`); the
notebook has no identity section. If you are porting code from the long-form build, replace
that handle with a `SET_EDA_CTX` call before the statement.

### Identity changes disappear after a rebuild

The policies are installed by `python app/scripts/setup_deep_security.py` (idempotent); re-run it after `seed.py`. The notebooks are generated from `.nbwork/parts` (see the README's maintainer section): edit the parts, never the `.ipynb`.

---

## LangChain interop (Part 3)

**`ModuleNotFoundError: No module named 'langchain_oracledb'`** — the kernel is missing the interop package. It is part of `requirements.txt`; on a Codespace re-run `bash .devcontainer/setup_build.sh`, locally `pip install -r requirements.txt`.

**`RuntimeError: Failed due to a DB error: ORA-29879: cannot create multiple domain indexes on a column list using same indextype`** — you asked `create_hybrid_index` for a table that already has a standalone vector index and an Oracle Text index (`OracleVS.from_texts` + `create_text_index` produce exactly that pair). A hybrid index *is* both, so it needs its own table. To try the hybrid retriever, create an `OracleVS` table, drop the vector index LangChain created on it, then create the hybrid index.

**`OracleTextSearchRetriever` returns nothing for a natural-language question** — Oracle Text wants an *expression*, not a sentence: `amount_cents OR cents OR USD`, or `operator_search=True` with your own `AND`/`OR`/`NEAR` operators. It also needs a text index on the column (`create_text_index`, §3.1).

## Checking System Status

If something isn't working and you're not sure where, run this diagnostic cell:

```python
import oracledb, os

print("=== Environment ===")
for k in ("OPENAI_API_KEY", "OCI_GENAI_API_KEY", "LLM_PROVIDER", "LLM_MODEL"):
    v = os.environ.get(k)
    print(f"  {k}: {'SET' if v else 'NOT SET'}")

print("\n=== Oracle Connection ===")
try:
    conn = oracledb.connect(user="AGENT", password="AgentPwd_2025",
                            dsn="localhost:1521/FREEPDB1")
    cur = conn.cursor()
    cur.execute("SELECT BANNER FROM v$version WHERE rownum = 1")
    print("  AGENT user:", cur.fetchone()[0])
    cur.execute("SELECT model_name FROM user_mining_models")
    print("  ONNX models:", [r[0] for r in cur])
    cur.execute("SELECT COUNT(*) FROM all_tables WHERE owner = 'FINANCE'")
    print("  FINANCE tables:", cur.fetchone()[0])
    conn.close()
except Exception as e:
    print("  AGENT connection: FAILED:", e)

print("\n=== Vector Memory ===")
try:
    conn = oracledb.connect(user="sys", password="OraclePwd_2025",
                            dsn="localhost:1521/FREEPDB1",
                            mode=oracledb.AUTH_MODE_SYSDBA)
    cur = conn.cursor()
    cur.execute("SELECT value FROM v$parameter WHERE name = 'vector_memory_size'")
    val = int(cur.fetchone()[0] or 0)
    print(f"  vector_memory_size: {val // (1024**2)}M" if val > 0 else "  vector_memory_size: 0 (HNSW will fail)")
    conn.close()
except Exception as e:
    print("  SYS connection: FAILED:", e)
```

Share the output with the facilitator if you need help.
