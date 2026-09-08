# Part 2: Long-Term Memory with OAMP

## What Is Agent Memory?

An LLM has no persistent state between calls. Every inference starts from scratch. **Agent memory** is the infrastructure that gives agents the ability to remember across turns, sessions, and tasks — the institutional knowledge an analyst accumulates after months of working with a database.

In this workshop the long-term store **is** the [Oracle AI Agent Memory Package (OAMP)](https://www.oracle.com/database/ai-agent-memory/).

Instead of hand-rolling a `knowledge` / `conversation` / `tool_log` schema, we hand a connection to `OracleAgentMemory` and let it own the DDL, the embedding pipeline, and the retrieval surface.

| OAMP primitive | What it stores | Replaces |
|---|---|---|
| `memory` (via `client.add_memory`) | Durable facts — scanned schema entries, user corrections, tool outputs (with metadata). | `institutional_knowledge`, `tool_log` |
| `thread` (via `client.create_thread`) | A conversation. Holds messages and exposes a context card. | `conversation` |
| `context_card` (via `thread.get_context_card`) | Compact, query-relevant block of memories + recent turns. | The hand-rolled `build_context` |

We **do** keep one bespoke table — `scan_history`. It records *that* a scan ran, not *what was learned*. It'''s **procedural** memory of the agent'''s own actions, queried by time/owner not by meaning, so we put it in a regular indexed table rather than OAMP.

## How OAMP Is Wired Up

The pre-built setup cell wires OAMP with three things you'''ll see referenced in the Python code:

```python
memory_client = OracleAgentMemory(
    connection=agent_conn,                            # AGENT-owned schema
    embedder=OracleONNXEmbedder(agent_conn),          # in-DB ONNX from §1 — no network
    llm=extraction_llm,                               # same chat provider/model as §1
    extract_memories=True,                            # mine durable facts from threads
    schema_policy="create_if_necessary",              # OAMP owns its DDL
    table_name_prefix="eda_onnx_",
)
```

Three things to notice:

1. **`agent_conn`** — OAMP-managed tables live in the `AGENT` schema, not `SYS`.
2. **`OracleONNXEmbedder`** — wraps `SELECT VECTOR_EMBEDDING(ALL_MINILM_L12_V2 USING :t AS DATA) FROM dual`. Every embed call is a SQL statement on `agent_conn`. Zero network calls for embedding.
3. **`extraction_llm`** — OAMP uses the same chat model your agent uses to extract durable memories from threads and maintain a rolling summary.

`schema_policy="create_if_necessary"` means OAMP creates `eda_onnx_memory`, `eda_onnx_thread`, `eda_onnx_record_chunks`, etc. on first use. You never write DDL for memory tables.

## OAMP user and agent IDs (auto-registered)

Every memory record OAMP stores carries a `user_id` (the operator) and an `agent_id` (which agent wrote it). The pre-built `build_memory_client` call in the notebook (`memory_client = OracleAgentMemory(...)`) registers these IDs idempotently — you don't need a separate registration step. The IDs `enterprise-operator` and `enterprise-data-agent` are wired through the rest of the harness.

## The Schema Scanner: Catalog Views as Training Data

Tables are storage. **Retrieval** is what makes them useful. The agent'''s "enterprise awareness" comes from a scanner that reads Oracle'''s catalog views and converts each fact into a natural-language entry that goes into OAMP, embedded and ready for semantic retrieval.

We mine **four** sources:

1. **Structural** — `ALL_TABLES`, `ALL_TAB_COLUMNS`: names, types, nullability. *What shapes exist.*
2. **Annotation** — `ALL_TAB_COMMENTS`, `ALL_COL_COMMENTS`: human-written descriptions. *What a domain expert said.*
3. **Relational** — `ALL_CONSTRAINTS`, `ALL_CONS_COLUMNS`: PK/FK. *How tables relate.*
4. **Workload** — `V$SQL`: a sample of recent queries. *How the database is actually used.*

> **Why store scanned facts as *text* with embeddings, not as normalized rows?** Because the agent retrieves by *meaning*, not by primary key. When the user asks "which table has the voyage manifest?" we want a cosine search over embedded descriptions to surface `SUPPLYCHAIN.CONTAINERS`, not a JOIN through four catalog views.

Each scanner helper takes `(conn, owner)` and returns a `list[Fact]`:

```python
@dataclass
class Fact:
    kind: str        # "table" | "column" | "relationship" | "query_pattern"
    subject: str     # e.g. "SUPPLYCHAIN.VESSELS"
    body: str        # natural-language sentence the embedder will read
    metadata: dict   # owner, table, column, etc.
```

## TODO 1: Implement `_scan_tables`

This is the simplest of the four scanners — and it'''s the right place to learn the pattern. It mines `ALL_TABLES` joined with `ALL_TAB_COMMENTS` and emits one `Fact(kind="table")` per table.

**The query you need to run:**

```sql
SELECT t.table_name, tc.comments, t.num_rows, t.last_analyzed
  FROM all_tables t
  LEFT JOIN all_tab_comments tc
    ON tc.owner = t.owner AND tc.table_name = t.table_name
 WHERE t.owner = :owner
 ORDER BY t.table_name
```

**For each row**, build a natural-language `body` that the embedder can index:

> `"Table SUPPLYCHAIN.VESSELS. Documented purpose: Individual ships owned/operated by carriers. Approximate row count: 30. Statistics last gathered at 2026-05-09 12:34:00."`

Concatenate the parts conditionally — skip the comment line if there'''s no comment, skip the row count if `num_rows` is `None`, etc.

**Solution:**

```python
def _scan_tables(conn, owner: str) -> list[Fact]:
    sql = (
        "SELECT t.table_name, tc.comments, t.num_rows, t.last_analyzed "
        "  FROM all_tables t "
        "  LEFT JOIN all_tab_comments tc "
        "    ON tc.owner = t.owner AND tc.table_name = t.table_name "
        " WHERE t.owner = :owner "
        " ORDER BY t.table_name"
    )
    facts: list[Fact] = []
    with conn.cursor() as cur:
        cur.execute(sql, owner=owner.upper())
        for table, comment, num_rows, last_analyzed in cur:
            body_parts = [f"Table {owner}.{table}."]
            if comment:
                body_parts.append(f"Documented purpose: {comment}")
            if num_rows is not None:
                body_parts.append(f"Approximate row count: {num_rows:,}.")
            if last_analyzed:
                body_parts.append(f"Statistics last gathered at {last_analyzed}.")
            facts.append(Fact(
                kind="table",
                subject=f"{owner}.{table}",
                body=" ".join(body_parts),
                metadata={
                    "owner": owner,
                    "table": table,
                    "num_rows": num_rows,
                    "has_comment": bool(comment),
                },
            ))
    return facts
```

The other three scanners (`_scan_columns`, `_scan_relationships`, `_scan_workload`) follow the same pattern and are pre-built — read them after you finish this TODO and notice how each one converts a different catalog view into the same `Fact` shape.

## How Facts Become Memories

After the four scanners run, the pre-built `write_facts()` function:

1. Computes `body_hash = sha256(fact.body)` — used for change detection.
2. Looks up an existing memory with the same `(kind, subject)` metadata.
3. **If absent** — calls `memory_client.add_memory(...)` (which embeds + inserts).
4. **If present and `body_hash` unchanged** — skips the embed call entirely.
5. **If present and `body_hash` changed** — deletes the stale row, inserts the new one.

The hash check is what makes hourly re-scans free. The vast majority of calls hash-check and skip; only schema changes trigger an embed.

## Key Takeaways — Part 2

- **Don'''t hand-roll the memory schema.** OAMP gives you `memory`, `thread`, and `context_card`. Skipping it costs weeks of bookkeeping code that has nothing to do with the agent'''s actual job.
- **Catalog views are training data.** `ALL_TABLES + ALL_TAB_COLUMNS + ALL_CONSTRAINTS + V$SQL` mined into prose facts is how you teach an agent your schema without fine-tuning a model.
- **`body_hash` makes re-scans free.** The scanner only re-embeds facts whose underlying text changed. Hourly re-scans become viable when the dedup is content-based, not time-based.
- **Procedural memory is different.** `scan_history` (when/how the agent ran) is queried by time and owner, not by meaning — keep it as a regular indexed table, not an OAMP memory.

## Troubleshooting

**`ValueError: user already exists`** — OAMP's `add_user` and `add_agent` reject duplicate IDs. The pre-built `memory_client` initialisation in §2.2 wraps these calls in `try/except ValueError`, but if you call them yourself, do the same.

**`ORA-00942: table or view does not exist`** — `ALL_TABLES` etc. are catalog views every user can read. If you see this, you'''re probably querying as a user without `SELECT_CATALOG_ROLE` (the setup cell granted it).

**Scanner returns 0 facts** — Check the `owner` argument is the schema name in uppercase. `ALL_TABLES.owner` is always uppercase even if you `CREATE USER demo`.
