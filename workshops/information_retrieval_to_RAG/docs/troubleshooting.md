# Troubleshooting Guide

This guide covers the most common issues encountered during the Information Retrieval to RAG Workshop and how to resolve them.

---

## Oracle Database Issues

### ORA-51962: The vector memory area is out of space

**Symptom:** Running the HNSW index creation cell produces this error:

```
RuntimeError: Failed due to a DB error: ORA-51962: The vector memory area is out of space for the current container.
```

**Cause:** `vector_memory_size` is set to 0 in the running Oracle instance. This means the setup script did not complete successfully, or the parameter was not applied before the notebook was opened.

**Fix:** Run this in a notebook cell or the terminal:

```python
import oracledb

conn = oracledb.connect(
    user="sys",
    password="OraclePwd_2025",
    dsn="localhost:1521/FREE",
    mode=oracledb.SYSDBA
)
conn.cursor().execute("ALTER SYSTEM SET vector_memory_size = 1G SCOPE=BOTH")
conn.commit()
conn.close()
print("Done — re-run the index creation cell.")
```

No restart needed. Go straight back to the index creation cell.

---

### ORA-12541 / Connection refused

**Symptom:** Any database connection attempt fails with `Connection refused` or `DPY-6005`.

**Cause:** The Oracle container is not running.

**Fix:** Open a terminal and run:

```bash
docker ps
```

If `oracle-free` is not listed, start it:

```bash
docker compose -f .devcontainer/docker-compose.yml up -d oracle
```

Then wait 30 seconds and retry the connection cell.

---

### ORA-01017: Invalid username or password

**Symptom:** The VECTOR user connection fails with an authentication error.

**Cause:** The container restarted with a stale volume that has different credentials.

**Fix:**

```bash
docker exec oracle-free resetPassword OraclePwd_2025
```

Then retry the connection cell.

---

### Oracle container starts but never becomes ready

**Symptom:** The setup script runs through all 20 attempts and exits with `ERROR: Oracle did not start`.

**Cause:** I/O slowness on the underlying Codespace disk is causing Oracle's redo log writer to stall, making the listener unresponsive even though Oracle is technically running.

**Fix:** Check the Oracle logs to confirm it is actually running:

```bash
docker logs oracle-free 2>&1 | tail -20
```

If you see `DATABASE IS READY TO USE!` in the output, Oracle is up. Run the setup manually:

```bash
bash .devcontainer/setup_runtime.sh
```

If the issue persists, stop and restart the Codespace from the GitHub UI — this provisions a fresh machine with better I/O.

---

## Codespace and Environment Issues

### Codespace shows "Setting up your Codespace" for more than 10 minutes

**Symptom:** The Codespace is stuck on the loading screen.

**Cause:** The `postCreateCommand` is running `setup_runtime.sh`, which includes Oracle startup. This takes 3-5 minutes on a cold start.

**Fix:** This is expected behaviour. Do not refresh the page. Wait for the "Workshop is ready!" banner in the terminal. If it exceeds 10 minutes, open a new terminal and run:

```bash
docker logs oracle-free 2>&1 | tail -20
```

---

### Jupyter kernel not found or "Information Retrieval to RAG Workshop" kernel missing

**Symptom:** The notebook asks you to select a kernel and the workshop kernel is not listed.

**Cause:** The `onCreateCommand` (pip install + kernel registration) did not complete, possibly because the prebuild failed.

**Fix:**

```bash
pip install -q ipykernel && python -m ipykernel install --user --name python3 --display-name "Information Retrieval to RAG Workshop"
```

Then reload the VS Code window (`Cmd/Ctrl + Shift + P` -> `Developer: Reload Window`) and select the kernel again.

---

### API key not found / `OPENAI_API_KEY` is None

**Symptom:** A cell fails because `os.environ.get("OPENAI_API_KEY")` returns `None`.

**Cause:** The Codespaces secret was added after this Codespace was created, so it was not injected at startup.

**Fix:** Stop the Codespace and create a new one. Secrets are only injected at creation time. Alternatively, set the key manually for this session only:

```python
import os
os.environ["OPENAI_API_KEY"] = "sk-..."  # paste your key here
```

Do not commit this to git.

---

### `ipywidgets` rendering error in output cell

**Symptom:** A cell output shows `Error rendering output item using jupyter-ipywidget-renderer`.

**Fix:**

```bash
pip install -q ipywidgets
```

Then restart the kernel (`Kernel` -> `Restart Kernel`) and re-run the cell.

---

## Package Issues

### `ImportError` for `sentence_transformers` or `openai`

**Symptom:** A cell fails with `ModuleNotFoundError`.

**Cause:** The prebuild pip install did not complete, or the wrong kernel is selected.

**Fix:** Confirm you are using the `Information Retrieval to RAG Workshop` kernel (shown in the top right of the notebook). Then run:

```bash
pip install -q openai sentence-transformers oracledb
```

---

### Sentence-transformers model download is slow or times out

**Symptom:** The `SentenceTransformer` cell hangs for several minutes on first run.

**Cause:** The nomic-embed-text-v1.5 model is being downloaded from HuggingFace on first use. This is a ~550MB download.

**Fix:** This is expected on first run. Wait for the download to complete — it will be cached for all subsequent cells. Do not interrupt the cell.

---

## Checking System Status

If something is not working and you are not sure where the problem is, run this diagnostic cell:

```python
import oracledb, os

print("=== Environment ===")
print("OPENAI_API_KEY:", "SET" if os.environ.get("OPENAI_API_KEY") else "NOT SET")

print("\n=== Oracle Connection ===")
try:
    conn = oracledb.connect(user="VECTOR", password="VectorPwd_2025", dsn="localhost:1521/FREEPDB1")
    cur = conn.cursor()
    cur.execute("SELECT 'connected' FROM dual")
    print("VECTOR user:", cur.fetchone()[0])
    conn.close()
except Exception as e:
    print("VECTOR user: FAILED:", e)

print("\n=== Vector Memory ===")
try:
    conn = oracledb.connect(user="sys", password="OraclePwd_2025", dsn="localhost:1521/FREE", mode=oracledb.SYSDBA)
    cur = conn.cursor()
    cur.execute("SELECT value FROM v$parameter WHERE name = 'vector_memory_size'")
    val = int(cur.fetchone()[0])
    print(f"vector_memory_size: {val // (1024**2)}M" if val > 0 else "vector_memory_size: 0 (HNSW index will fail)")
    conn.close()
except Exception as e:
    print("SYS connection: FAILED:", e)
```

Share the output of this cell with the facilitator if you need help.
