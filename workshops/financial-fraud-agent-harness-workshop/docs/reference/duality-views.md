# JSON Relational Duality Views

> **Documentation:** [`Creating Duality Views`](https://docs.oracle.com/en/database/oracle/oracle-database/26/jsnvu/creating-duality-views.html)


> 🧭 **Advanced reference.** Duality views are not part of the notebook. `account_dv` and `customer_dv` are seeded by `app/scripts/seed.py`, the running app exposes `get_document` / `query_documents`, and the app registers `account_document`, which falls back to the same document built with SQL/JSON when the view cannot run (see the caveat below). The notebook does not use it.
[Part 4](../part-4-tools-and-skills.md) gave the agent a vector-indexed `toolbox` (dispatchable functions) and [Part 5](../part-5-agent-loop.md) layered the agent loop on top. **Duality views add a third shape: document-shaped reads of the relational schema** via Oracle 23ai/26ai's JSON Relational Duality Views.

A duality view is a JSON projection over a set of tables joined by PK/FK/UK relationships. The same row in `accounts` is accessible as a **relational tuple** *and* as a **nested JSON document** that includes its `customer`, `branch`, and the arrays of `cards` and `transactions` (with their `merchant` nested inside). One read, no JOINs, no client-side reshaping.

![JSON Relational Duality — three lenses, one source of truth](../../images/cover-duality-view.png)

## Why this matters for an LLM agent specifically

GPT-class models reason about JSON markedly better than they reason about tabular join results. Every time the agent asks *"tell me everything about account 7"*, the choice today is: write a 4-table JOIN, parse the rows, mentally reassemble the document. With a duality view the agent runs:

```sql
SELECT JSON_SERIALIZE(data PRETTY) FROM account_dv WHERE JSON_VALUE(data, '$._id') = 7
```

and gets the document back already shaped. Fewer tool turns, fewer hallucinated columns.

## Why this matters for the harness specifically

One `SELECT JSON_SERIALIZE(data)` returns a fully nested document — customer, branch, cards, and transactions with their merchant — in a single tool call, instead of the agent composing a multi-table JOIN and mentally reassembling the shape.

## The two duality views

| View | Shape | When the agent reaches for it |
|---|---|---|
| `account_dv` | account → customer; account → branch; account → cards[]; account → transactions[] | Whole-account queries: *"what's on account X?"*, *"all cards for account 7"* |
| `customer_dv` | customer → accounts[]; customer → loans[]; account → branch | Customer queries: *"which loans does customer Y hold?"* |

Both are read-only — no `WITH UPDATE` clause, so DML through them is rejected by the kernel.

> ⚠️ **On this Free image, a duality view and kernel identity can collide.** Oracle's DV engine
> cannot read a view whose base table carries more than one `DBMS_RLS` policy (the [Deep Data Security reference](deep-data-security.md) puts a region
> predicate plus an amount mask on `FINANCE.ACCOUNTS`). The view DDL succeeds and the dictionary
> reports it `VALID`, but every `SELECT` fails with a misleading `ORA-40606: Table 'ACCOUNTS' does
> not have a primary or unique key` — the PK is intact. The app (and its
> `account_document`) therefore try the view first and fall back to the same document built with
> `JSON_OBJECT`/`JSON_ARRAYAGG` over the base tables: VPD still applies to that query, so only the
> projection mechanism changes, not the trust boundary. Run
> `python app/scripts/bootstrap.py && python app/scripts/seed.py` on a fresh volume and you will see
> the view read fine **until** `setup_deep_security.py` installs the policies.

## Reference: Register `tool_get_document`

Read one full document from a duality view by primary key. The agent calls this instead of writing JOINs whenever it needs the full shape of an entity.

`view` must be one of `account_dv` / `customer_dv`. `key` is the value of the document `_id`. Return the JSON document as a string, or a JSON `{"error": ...}` if the view name is unknown or no document matches.

The query you need:

```sql
SELECT JSON_SERIALIZE(data PRETTY) FROM FINANCE.{view} WHERE JSON_VALUE(data, '$._id') = :k
```

Bind `key` as an integer when it parses as a digit, otherwise as a string.

**Solution:**

```python
@register
def tool_get_document(view: str, key: str) -> str:
    """Read one full document from a JSON Relational Duality View by primary key.
    Use this instead of writing JOINs whenever you need the full shape of an entity
    (an account with its customer/branch/cards/transactions, or a customer with its
    accounts/loans). Returns a JSON document.

    `view` must be one of: account_dv, customer_dv.
    `key` is the value of the document _id (numeric account_id or customer_id, as a string).
    """
    allowed = {"account_dv", "customer_dv"}
    if view not in allowed:
        return json.dumps({"error": f"unknown view {view!r}; allowed: {sorted(allowed)}"})
    try:
        with agent_conn.cursor() as cur:
            cur.execute(
                f"SELECT JSON_SERIALIZE(data PRETTY) FROM {DEMO_USER}.{view} "
                f" WHERE JSON_VALUE(data, '$._id') = :k",
                k=int(key) if str(key).isdigit() else key,
            )
            row = cur.fetchone()
        if not row:
            return json.dumps({"error": f"no document with _id={key} in {view}"})
        body = row[0].read() if hasattr(row[0], "read") else str(row[0])
        return body
    except Exception as e:
        return json.dumps({"error": f"{type(e).__name__}: {e}"})
```

`tool_query_documents(view, where, max_rows)` — for filtering a duality view with a SQL predicate — is pre-built right after this TODO.

## Writable views with ETag-based concurrency

A duality view whose definition carries `WITH UPDATE` is writable: `UPDATE <view> SET data = …` writes back to the underlying base tables, atomically, with the row policies still enforced.

Two pieces make that safe in a multi-writer world:

| Piece | Purpose |
|---|---|
| `WITH UPDATE` clause | Tells the kernel the view is writable; without it, `UPDATE` raises `ORA-42692` |
| `_metadata.etag` field on every retrieved document | Optimistic concurrency. Stale writes raise `ORA-42699` |

This is the same model HTTP uses for `If-Match` headers — but enforced **inside the database**, by the SQL engine, on every UPDATE through the view. No application-layer locking, no `SELECT … FOR UPDATE` fan-out, no client-side cache reconciliation logic. To try it, add `WITH UPDATE` to a copy of the view DDL in `app/backend/db/seed_finance.py` and re-run `seed.py`:

1. **Round-trip:** read a document, flip a field, write it back with the matching ETag. The ETag rotates atomically.
2. **Conflict:** two readers grab the same document. First writer commits; second writer's ETag is now stale and the kernel raises `ORA-42699`.

## Why we don't expose the writable path to the agent

The harness keeps `tool_run_sql` SELECT-only and there's no `tool_update_document`. Adding one would re-open the write path we closed — a hostile prompt could rewrite transaction status or account balances. The cells below are SQL-level demonstrations of the duality mechanic, not agent capabilities. If you decide to give your agent narrow write authority later (e.g., status updates only, gated by an identity check), this is the foundation you'd build on.

## Key takeaways

- **One row, two equally-valid shapes.** A duality view serves the SAME data as a relational tuple AND a JSON document — kernel-managed, no app-layer mapping. The relational schema is the truth; the JSON shape is the contract.
- **Three personas, one source.** A DBA, an AI developer, and an AI agent all consume the same row through their preferred lens (SQL, REST/JSON, tool dispatch). Defining the projection once kills the per-consumer mapping code.
- **Writable views need `WITH UPDATE`.** Without it, `UPDATE …` raises `ORA-42692`. With it, you get server-side optimistic concurrency for free — every doc carries `_metadata.etag`, stale writes raise `ORA-42699`.

## Troubleshooting

**`ORA-00900` / `ORA-02000` on `CREATE OR REPLACE JSON RELATIONAL DUALITY VIEW`** — Your Oracle image predates duality view support. Confirm with `SELECT BANNER_FULL FROM v$version`. Duality views require Oracle 23ai or later.

**`ORA-42699: can't update through duality view because the document's etag is out of date`** — Expected in the conflict demo. In real code, the second writer would re-read the row, re-apply its change, and retry.

**`ORA-42692: cannot UPDATE/DELETE through duality view`** — The view is read-only (no `WITH UPDATE` clause). Either change the view or use the underlying table.
