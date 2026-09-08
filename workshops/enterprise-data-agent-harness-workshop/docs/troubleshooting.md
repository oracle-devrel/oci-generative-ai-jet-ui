# Troubleshooting Guide

This guide covers the most common issues encountered during the Enterprise Data Agent Workshop and how to resolve them.

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

**Symptom:** `DBMS_VECTOR.RERANK` falls back to plain cosine ordering with `ORA-04036`.

**Cause:** The Free image ships with `pga_aggregate_limit = 2G`, which is too tight for the reranker'''s transient PGA use.

**Fix:** Raise it at the CDB level (PDBs can'''t change this parameter):

```bash
docker exec -i oracle-free sqlplus -s / as sysdba <<'''SQL'''
ALTER SESSION SET CONTAINER = CDB$ROOT;
ALTER SYSTEM SET pga_aggregate_limit = 4G SCOPE=BOTH;
EXIT
SQL
```

`SCOPE=BOTH` means the change applies live and persists across restarts. No bounce needed.

---

### ORA-12541 / Connection refused

**Symptom:** Any database connection attempt fails with `Connection refused` or `DPY-6005`.

**Cause:** The Oracle container isn'''t running.

**Fix:**

```bash
docker ps
```

If `oracle-free` isn'''t listed, start it (the §1 setup cell does this on first run):

```bash
docker start oracle-free
```

Wait 30 seconds and retry the connection cell.

---

### ORA-01017: Invalid username or password

**Symptom:** Connecting as `AGENT` fails with an authentication error.

**Cause:** The §1 bootstrap cell didn'''t run — `AGENT` doesn'''t exist yet. Or the container was rebuilt with a stale volume.

**Fix:** Re-run the bootstrap cell (it creates `AGENT` if missing). If the issue persists:

```bash
docker exec oracle-free resetPassword OraclePwd_2025
```

Then re-run the bootstrap cell.

---

### Oracle container starts but never becomes ready

**Symptom:** `docker ps` shows `oracle-free` running, but the connection cell still fails.

**Cause:** Oracle'''s listener takes a few seconds longer than the container healthcheck signals.

**Fix:** Check the logs:

```bash
docker logs oracle-free 2>&1 | tail -20
```

If you see `DATABASE IS READY TO USE!`, Oracle is up. The pre-built `connect()` helper retries automatically; if it'''s still failing after 5 attempts, restart the kernel and try again.

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

**Cause:** The Codespaces secret was added after this Codespace was created, so it wasn'''t injected at startup. (Secrets are only injected at creation time.)

**Fix:** Set the key manually for this session only:

```python
import os
os.environ["OPENAI_API_KEY"] = "sk-..."     # or
os.environ["OCI_GENAI_API_KEY"] = "..."
```

Do not commit this to git. For permanent fixes, stop the Codespace, add the secret in repo settings, and create a new one.

---

### Jupyter kernel "Python 3.11" not found

**Symptom:** The notebook asks you to select a kernel and Python 3.11 isn'''t listed.

**Fix:**

```bash
pip install -q ipykernel && python -m ipykernel install --user --name python3 --display-name "Python 3.11"
```

Reload the VS Code window (`Cmd/Ctrl + Shift + P` → `Developer: Reload Window`) and select the kernel again.

---

## OAMP / Memory Issues

### `ValueError: user already exists` (or agent already exists)

**Symptom:** A cell that calls `memory_client.add_user(...)` or `memory_client.add_agent(...)` raises `ValueError: user already exists`.

**Cause:** The user/agent was registered on a prior run; OAMP rejects duplicates.

**Fix:** Wrap the calls in `try/except ValueError` and check for `"already exists"` in the message — see the [Part 2 guide](part-2-oamp-memory.md).

---

### Scanner returns 0 facts

**Symptom:** `run_scan(agent_conn, owner=DEMO_USER)` reports `facts_total = 0`.

**Cause:** The `owner` argument is case-sensitive at the SQL layer (`ALL_TABLES.owner` is always uppercase). Or the SUPPLYCHAIN seed cell didn'''t complete.

**Fix:** Confirm the user exists and has tables:

```python
with sys_conn.cursor() as cur:
    cur.execute("SELECT COUNT(*) FROM all_tables WHERE owner = '"'"'SUPPLYCHAIN'"'"'")
    print("table count:", cur.fetchone()[0])
```

Should print `7`. If `0`, re-run the seed cell.

---

### `retrieve_knowledge` returns no results

**Symptom:** Calling `retrieve_knowledge` after a successful scan returns an empty list.

**Cause:** The ONNX embedder didn'''t register, or the `kinds=` filter is too restrictive.

**Fix:** Check the embedder is loaded:

```python
with agent_conn.cursor() as cur:
    cur.execute("SELECT model_name FROM user_mining_models")
    print(list(cur))
```

Should include `ALL_MINILM_L12_V2`. If empty, the §1 ONNX load cell didn'''t run.

For `kinds=`, try without a filter first to confirm there are memories at all:

```python
retrieve_knowledge("table", k=5)  # no kinds filter
```

---

## Tool Issues

### `ValueError: tool 'foo' has no docstring`

**Symptom:** `@register` raises this error.

**Cause:** The `_build_schema` helper requires a non-empty docstring — it'''s the tool'''s public spec, embedded for retrieval.

**Fix:** Add a docstring describing what the tool does and *when* to call it. "Use this when..." is good phrasing.

---

### `openai.BadRequestError: 400 ... messages with role 'tool' must be a response to a preceding message with 'tool_calls'`

**Symptom:** The agent loop raises this on the second LLM call.

**Cause:** You appended a `tool` message to `messages` without first appending the assistant'''s `tool_calls` message.

**Fix:** Make sure the loop body is in this order:

1. `resp = chat(messages, tools=tool_schemas)`
2. **Append the assistant message with `tool_calls`** to `messages`
3. For each `tc` in `msg.tool_calls`, dispatch and append a `tool` message with `tool_call_id=tc.id`

See [Part 7 guide](part-7-agent-loop.md) for the exact pattern.

---

### Agent calls the same tool with the same args repeatedly

**Symptom:** The trace shows the same `(tool, args)` over and over until budget exhaustion.

**Cause:** GPT-class models occasionally loop on a tool when the result is empty or unhelpful.

**Fix:** The complete-notebook version of `agent_turn` adds a 3-deep dedupe — short-circuiting identical dispatches. For the workshop demo, keep `max_iterations` low (≤ 8) and let the budget catch it.

---

## DDS / Identity Issues

### ORA-00900 / ORA-00901 on `CREATE DATA SECURITY POLICY`

**Symptom:** The §6 policy DDL fails with `ORA-00900` or `ORA-00901`.

**Cause:** Your Oracle image predates the declarative DDS surface introduced in 26ai. The notebook automatically falls back to `DBMS_RLS` — same semantics, slightly different syntax.

**Fix:** Confirm the DDS_MODE prints `dbms_rls` after the cell. If both paths fail, the issue is grants — `GRANT EXECUTE ON SYS.DBMS_RLS TO SUPPLYCHAIN` as `SYSDBA`.

---

### Both identities return the same rows

**Symptom:** The CFO and APAC fleet manager see identical results.

**Cause:** `EDA_CTX` wasn'''t set on the connection.

**Fix:** Verify directly:

```python
set_identity("cfo@acme.com", "EXECUTIVE")
with agent_conn.cursor() as cur:
    cur.execute("SELECT SYS_CONTEXT('"'"'EDA_CTX'"'"', '"'"'END_USER'"'"'), SYS_CONTEXT('"'"'EDA_CTX'"'"', '"'"'CLEARANCE'"'"') FROM dual")
    print(cur.fetchone())
```

Should print `('"'"'cfo@acme.com'"'"', '"'"'EXECUTIVE'"'"')`. If `(None, None)`, the procedure call failed silently — re-run the §6 setup cell.

---

## Checking System Status

If something isn'''t working and you'''re not sure where, run this diagnostic cell:

```python
import oracledb, os

print("=== Environment ===")
for k in ("OPENAI_API_KEY", "OCI_GENAI_API_KEY", "LLM_PROVIDER", "LLM_MODEL"):
    v = os.environ.get(k)
    print(f"  {k}: {'"'"'SET'"'"' if v else '"'"'NOT SET'"'"'}")

print("\n=== Oracle Connection ===")
try:
    conn = oracledb.connect(user="AGENT", password="AgentPwd_2025",
                            dsn="localhost:1521/FREEPDB1")
    cur = conn.cursor()
    cur.execute("SELECT BANNER FROM v$version WHERE rownum = 1")
    print("  AGENT user:", cur.fetchone()[0])
    cur.execute("SELECT model_name FROM user_mining_models")
    print("  ONNX models:", [r[0] for r in cur])
    cur.execute("SELECT COUNT(*) FROM all_tables WHERE owner = '"'"'SUPPLYCHAIN'"'"'")
    print("  SUPPLYCHAIN tables:", cur.fetchone()[0])
    conn.close()
except Exception as e:
    print("  AGENT connection: FAILED:", e)

print("\n=== Vector Memory ===")
try:
    conn = oracledb.connect(user="sys", password="OraclePwd_2025",
                            dsn="localhost:1521/FREEPDB1",
                            mode=oracledb.AUTH_MODE_SYSDBA)
    cur = conn.cursor()
    cur.execute("SELECT value FROM v$parameter WHERE name = '"'"'vector_memory_size'"'"'")
    val = int(cur.fetchone()[0] or 0)
    print(f"  vector_memory_size: {val // (1024**2)}M" if val > 0 else "  vector_memory_size: 0 (HNSW will fail)")
    conn.close()
except Exception as e:
    print("  SYS connection: FAILED:", e)
```

Share the output with the facilitator if you need help.
