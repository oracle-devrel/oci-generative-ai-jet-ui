# Troubleshooting

Common failures, what they mean, and how to fix them.

## Codespace bootstrap

### `docker logs oracle-free` shows `ORA-...` startup errors

Oracle Free can take 3–8 minutes to initialise on first boot. If the
container is still in `starting` state after 8 minutes:

```bash
docker logs --tail 100 oracle-free
```

Common cause: not enough RAM in the codespace. Oracle Free needs ~2 GB
of free memory just to start; the codespace image budget is tight.
Upgrade to a 4-core / 8 GB codespace if you see OOM kills.

### `bootstrap.py` failed with `ORA-01919: role does not exist`

The `bootstrap.py` script grants `DB_DEVELOPER_ROLE`, which doesn't
exist on every Oracle Free image. The script swallows that specific
error and continues. If it surfaced anyway, your image is missing one
of `CONNECT` / `RESOURCE` / `CREATE TABLE` instead — check the log:

```bash
tail -100 .devcontainer/logs/bootstrap.log
```

### `onnx_setup.py` failed downloading the ONNX zip

The default ONNX URL is Oracle's hosted pre-converted model. If the
download fails (network, expired link), override `ONNX_URL`:

```bash
export ONNX_URL="https://your-mirror/all_MiniLM_L12_v2_augmented.zip"
bash .devcontainer/setup_runtime.sh
```

### `seed_supplychain.py` says `ONNX model 'ALL_MINILM_L12_V2' is not loaded`

`bootstrap.py` and `onnx_setup.py` haven't completed. Re-run:

```bash
bash .devcontainer/setup_runtime.sh
```

The script is idempotent — re-running it skips work that's already done.

## Notebook

### `TODO 1` checkpoint: `❌ embedding length 1536 != 384`

You're using `OpenAIEmbeddings` instead of `OracleEmbeddings`. The
in-DB ONNX model produces **384-dim** vectors. Double-check your
import and constructor.

### `TODO 2` checkpoint: `similarity_search returned no rows`

The `supplychain_demand` table is empty. Re-run the seed step:

```bash
python app/scripts/seed_supplychain.py
```

### `TODO 3` checkpoint: `Priya's seeded memory wasn't found`

Either:

1. Your `table_suffix` doesn't match the seed script's
   (`"agent_memory"`). Fix the constructor.
2. The seed step never wrote the memories. Re-run
   `app/scripts/seed_supplychain.py` and check its output for
   `AsyncOracleStore: seeded user memories for priya, michael`.

### `TODO 4` setup fails with `ORA-00942: table 'CHECKPOINTS' does not exist` (on subsequent operations)

Symptom: `saver.setup()` returns success but `saver.alist(None)`
errors. Cause: the `CHECKPOINT_MIGRATIONS` table is stale from a
previous run with a different schema version. Drop the four checkpoint
tables and retry:

```sql
DROP TABLE checkpoints PURGE;
DROP TABLE checkpoint_writes PURGE;
DROP TABLE checkpoint_blobs PURGE;
DROP TABLE checkpoint_migrations PURGE;
```

Then re-run TODO 4's setup cell.

### `TODO 5` checkpoint: `r1.content != r2.content`

Cache isn't hitting. Two possibilities:

- `score_threshold=0.05` is too tight and the second prompt is being
  treated as a near-miss. Loosen to `0.1` or wider.
- You used `oracle_client` for the connection but a _different_
  embedder. The cache and the surrounding vector store should share
  the same embedder.

### `TODO 6` checkpoint: `semantic search only returned 0 hits`

`oracle_vs` is connected to an empty table. Same fix as TODO 2 — re-run
the seed.

### `TODO 7`/`TODO 8` checkpoint: agent missing `.name`

You forgot to pass `name="demand_analyst"` (or `"policy_agent"`) to
`create_agent`. Without `name`, the supervisor can't route to it.

### `TODO 9` checkpoint: answer doesn't reference Priya

The supervisor didn't call `policy_agent`, or the agent didn't invoke
`get_user_memory(user_id="priya")`. Check:

1. You compiled `supervisor_graph.compile(..., store=agent_store)`. If
   `store=` is missing, the long-term store is invisible inside the
   compiled graph.
2. Your request prompt includes the literal string `user_id=priya` so
   the agent's LLM can parse it.

### `TODO 9` checkpoint: answer doesn't reference the 500-IP policy threshold

The `policy_agent`'s `get_planner_policy` tool didn't fire, or it
returned a different document. Verify the policy memo is in OracleVS:

```python
print(oracle_vs.similarity_search("planner buy volume policy", k=1)[0].page_content)
```

You should see the text about `500 unique IPs`.

## Chat app

### Browser preview shows "502 Bad Gateway"

The Vite dev server (`:3000`) hasn't bound yet, or the FastAPI backend
(`:8000`) crashed during init. In a terminal:

```bash
ps aux | grep -E "(uvicorn|vite)" | grep -v grep
tail -60 .devcontainer/logs/backend.log
tail -60 .devcontainer/logs/frontend.log
```

Most common cause: Oracle wasn't ready when the backend tried to open
its connections. Re-run:

```bash
bash .devcontainer/start_app.sh
```

### `Architecture explorer` is empty / says "loading architecture…"

The `/api/agents` endpoint isn't reachable. Check the proxy in
`app/frontend/vite.config.ts` points at `http://localhost:8000` and the
backend is actually up.

### Tools never fire / supervisor returns instantly

The supervisor is short-circuiting because the model thinks it can
answer without delegating. Two fixes:

1. Make the system prompt more explicit about always delegating ("you
   MUST call `policy_agent` first").
2. Phrase the user request to require external data (mention a SKU
   category that isn't in the supervisor's training).

## Reset everything

Sometimes the only thing for it is to start fresh:

```bash
# Drop every Oracle table the workshop touched
python <<'PY'
import oracledb, os
c = oracledb.connect(user=os.environ["ORACLE_USER"], password=os.environ["ORACLE_PASSWORD"], dsn=os.environ["ORACLE_DSN"])
cur = c.cursor()
cur.execute("SELECT table_name FROM user_tables")
for (t,) in cur.fetchall():
    if any(t.upper().startswith(p) for p in ("STORE_", "CHECKPOINT", "VECTOR_MIGRATIONS_",
                                              "SUPPLYCHAIN_", "LANGCHAIN_")):
        try: cur.execute(f'DROP TABLE "{t}" CASCADE CONSTRAINTS PURGE')
        except Exception: pass
c.commit(); c.close()
PY

# Re-run bootstrap + onnx + seed
bash .devcontainer/setup_runtime.sh
```
