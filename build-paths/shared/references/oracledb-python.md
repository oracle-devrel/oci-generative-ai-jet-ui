# `oracledb` (Python driver) — the layer underneath LangChain

The beginner skill mostly hides this. The intermediate skill brushes it. The advanced skill uses it directly. This file is the reference for "what's actually happening under the wrapper."

Install: `pip install oracledb` (pure-Python "thin" mode by default — no Oracle client install needed).

## Connecting

```python
import oracledb
conn = oracledb.connect(
    user="SYSTEM",
    password=os.environ["ORACLE_PWD"],
    dsn="localhost:1521/FREEPDB1",
)
```

That's it for beginner / intermediate. `conn` gets handed to `OracleVS(client=conn, ...)` and you're done.

## Connection pools (intermediate / advanced)

For anything that's not a one-shot script — Gradio app, FastAPI server, agent loop:

```python
pool = oracledb.create_pool(
    user="SYSTEM",
    password=os.environ["ORACLE_PWD"],
    dsn="localhost:1521/FREEPDB1",
    min=2, max=10, increment=1,
)

with pool.acquire() as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT 1 FROM DUAL")
```

**Always use `with pool.acquire() as conn`** — the context manager releases back to the pool. Forgetting this is the #1 cause of "my app hangs after 10 requests."

Exemplars:
- `~/git/personal/oracle-aidev-template/app/db.py:1-50` — minimal lazy-init singleton.
- `apps/limitless-workflow/src/limitless/db/pool.py:1-50` — production pool with retry.

## Cursor basics (advanced)

```python
with conn.cursor() as cur:
    cur.execute("INSERT INTO MY_DOCS (id, content) VALUES (:id, :content)",
                id=1, content="hello")
    conn.commit()
    cur.execute("SELECT id, content FROM MY_DOCS WHERE id = :id", id=1)
    row = cur.fetchone()
```

Bind parameters use `:name` syntax. Don't string-format SQL — that's how SQL injection happens.

## Vector binds — the gotcha that wastes 30 minutes

When you bind a vector value to a SQL placeholder, Python lists do **not** work. You must use `array.array("f", values)`:

```python
import array
qv = array.array("f", [0.1, 0.2, 0.3, ...])  # 768 floats for nomic-embed-text
cur.execute(
    "SELECT id FROM MY_DOCS ORDER BY VECTOR_DISTANCE(embedding, :qv, COSINE) FETCH FIRST 5 ROWS ONLY",
    qv=qv,
)
```

Pass a plain list → silent type coercion failure or `DPY-3013`. Source: `apps/finance-ai-agent-demo/backend/retrieval/hybrid_search.py`.

## Returning generated values on insert

```python
new_id = cur.var(oracledb.NUMBER)
cur.execute("INSERT INTO MY_DOCS (content) VALUES (:c) RETURNING id INTO :new_id",
            c="text", new_id=new_id)
print(new_id.getvalue()[0])
```

Pattern from `~/git/personal/oracle-aidev-template/app/vector_search.py:30-80`.

## Async (advanced)

`oracledb.connect_async()` and `pool.acquire_async()` exist. Use them only when you're already inside an async stack — don't introduce async just to feel modern.

## ORA codes worth memorising

| Code | Means | Fix |
| --- | --- | --- |
| ORA-00942 | Table or view does not exist | The table wasn't created — `from_texts` first, or run schema DDL. |
| ORA-01017 | Invalid creds | `ORACLE_PWD` doesn't match the container; `docker compose down -v` to reset. |
| ORA-12541 | No listener | Container not up yet — wait for the healthcheck. |
| ORA-12514 | Service unknown | Use `FREEPDB1`, not `FREE`. |
| ORA-51805 | Vector dimension mismatch | Embedder dim ≠ column dim. Drop the table or pick a matching embedder. |
| DPY-3013 | Bind type error | You passed a Python list where Oracle wants `array.array("f", ...)`. |

## Don't do these

- Don't reinvent connection pooling with `threading.local`. Use `oracledb.create_pool`.
- Don't string-concat SQL. Bind variables.
- Don't keep a single connection alive for the lifetime of a multi-user app. Pool it.
- Don't `cur.execute(... ; commit;)`. Call `conn.commit()` separately, or set `autocommit=True` on the cursor (rare; explicit commits are clearer).
