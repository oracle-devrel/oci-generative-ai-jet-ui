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

We **do** keep one bespoke table — `scan_history`. It records *that* a scan ran, not *what was learned*. It's **procedural** memory of the agent's own actions, queried by time/owner not by meaning, so we put it in a regular indexed table rather than OAMP.

## How OAMP Is Wired Up

§2.1 builds the client:

```python
memory_client = OracleAgentMemory(
    connection=agent_conn,                            # AGENT-owned schema
    llm=extraction_llm,                               # same chat provider/model as Part 1
    memory_store_id="EDA_ONNX",                       # names the EDA_ONNX_* managed tables
    embedder=OracleDBEmbedder(agent_conn, model="ALL_MINILM_L12_V2", embedding_dimension=384),
    memory_extraction_config=MemoryExtractionConfig(extract_memories=True),  # mine durable facts
    schema_policy="create_if_necessary",              # OAMP owns its DDL
)
```

- **`agent_conn`**: OAMP-managed tables live in the `AGENT` schema, not `SYS`.
- **`OracleDBEmbedder`**: runs `VECTOR_EMBEDDING(ALL_MINILM_L12_V2 ...)` in the database. No network call for embedding.
- **`extraction_llm`**: the chat model OAMP uses to extract durable memories from threads and keep a rolling summary.
- **`schema_policy="create_if_necessary"`**: OAMP creates `EDA_ONNX_MEMORY`, `EDA_ONNX_THREAD`, `EDA_ONNX_RECORD_CHUNKS` and the rest on first use.

## TODO 2: `recall_memories`

§2.2. OAMP stores a fact with `add_memory` and finds it by meaning with `search`. Wrap `search` in `recall_memories(query, k=3, kind=None)` so later parts call one function.

Steps (two lines; the loop that turns hits into dicts is already written):

1. `flt` is the metadata filter: `{"kind": kind}` when `kind` is given, otherwise `None`.
2. `hits = memory_client.search(query, ...)` with these keyword arguments: `user_id=USER_ID`, `agent_id=AGENT_ID` (whose memories to search); `record_types=["memory"]` (stored facts only, not chat messages); `metadata_filter=flt` (a dict a memory's metadata must match, `None` = no filter); `max_results=k` (how many hits to return).

**Solution:**

```python
def recall_memories(query, k=3, kind=None):
    flt = {"kind": kind} if kind else None
    hits = memory_client.search(
        query, user_id=USER_ID, agent_id=AGENT_ID, record_types=["memory"],
        metadata_filter=flt, max_results=k)
    return [{"id": h.id, "kind": (h.metadata or {}).get("kind"),
             "subject": (h.metadata or {}).get("subject"),
             "body": h.content, "distance": h.distance} for h in hits]
```

The checkpoint stores one AML fact (`AMOUNT_CENTS` is in USD cents) and recalls it with a question that shares no words with it. It fails if the stub is unimplemented, returns nothing, or drops `user_id` / `agent_id`.

## OAMP user and agent IDs (auto-registered)

Every memory record OAMP stores carries a `user_id` (the operator) and an `agent_id` (which agent wrote it). `register_user_and_agent` (§2.1) registers these IDs idempotently. The IDs `enterprise-operator` and `enterprise-data-agent` are wired through the rest of the harness.

## The Schema Scanner: Catalog Views as Training Data

Tables are storage. **Retrieval** is what makes them useful. The agent's "enterprise awareness" comes from a scanner that reads Oracle's catalog views and converts each fact into a natural-language entry that goes into OAMP, embedded and ready for semantic retrieval.

We mine **four** sources:

1. **Structural** — `ALL_TABLES`, `ALL_TAB_COLUMNS`: names, types, nullability. *What shapes exist.*
2. **Annotation** — `ALL_TAB_COMMENTS`, `ALL_COL_COMMENTS`: human-written descriptions. *What a domain expert said.*
3. **Relational** — `ALL_CONSTRAINTS`, `ALL_CONS_COLUMNS`: PK/FK. *How tables relate.*
4. **Workload** — `V$SQL`: a sample of recent queries. *How the database is actually used.*

> **Why store scanned facts as *text* with embeddings, not as normalized rows?** Because the agent retrieves by *meaning*, not by primary key. When the user asks "which table records card transactions?" we want a cosine search over embedded descriptions to surface `FINANCE.TRANSACTIONS`, not a JOIN through four catalog views.

Each scanner helper takes `(conn, owner)` and returns a `list[Fact]`:

```python
@dataclass
class Fact:
    kind: str        # "table" | "column" | "relationship" | "query_pattern"
    subject: str     # e.g. "FINANCE.TRANSACTIONS"
    body: str        # natural-language sentence the embedder will read
    metadata: dict   # owner, table, column, etc.
```

## TODO 3: `_scan_tables`

§2.3. This is the simplest of the four scanners — and it's the right place to learn the pattern. It mines `ALL_TABLES` joined with `ALL_TAB_COMMENTS` and emits one `Fact(kind="table")` per table.

**The query (provided as `TABLES_SQL`):**

```sql
SELECT t.table_name, tc.comments, t.num_rows, t.last_analyzed
  FROM all_tables t
  LEFT JOIN all_tab_comments tc
    ON tc.owner = t.owner AND tc.table_name = t.table_name
 WHERE t.owner = :owner
 ORDER BY t.table_name
```

**For each row**, build a natural-language `body` that the embedder can index:

> `"Table FINANCE.TRANSACTIONS. Documented purpose: Card/account transactions. Approximate row count: 23606. Statistics last gathered at 2026-05-09 12:34:00."`

The cursor, the loop, the first sentence, the "Documented purpose" example and the statistics sentence are already written. You add two things (about 3 lines):

1. Following the "Documented purpose" example: when `num_rows` is not `None`, append the sentence `Approximate row count: {num_rows:,}.` to `parts` (`:,` adds thousands commas).
2. Append one `Fact` to `facts`: `Fact(kind, subject, body, metadata)` with kind `"table"`, subject `"{owner}.{table}"`, the `body` string, and a metadata dict with keys `owner`, `table`, `num_rows` and `has_comment` (`bool(comment)`).

**Solution:**

```python
def _scan_tables(conn, owner: str) -> list[Fact]:
    facts = []
    with conn.cursor() as cur:
        cur.execute(TABLES_SQL, owner=owner.upper())
        for table, comment, num_rows, last_analyzed in cur:
            parts = [f"Table {owner}.{table}."]
            if comment:
                parts.append(f"Documented purpose: {comment}")
            if num_rows is not None:
                parts.append(f"Approximate row count: {num_rows:,}.")
            if last_analyzed:
                parts.append(f"Statistics last gathered at {last_analyzed}.")
            body = " ".join(parts)
            facts.append(Fact("table", f"{owner}.{table}", body,
                              {"owner": owner, "table": table, "num_rows": num_rows, "has_comment": bool(comment)}))
    return facts
```

The other three scanners (`scan_columns`, `scan_relationships`, and the `V$SQL` workload scanner) follow the same pattern and are pre-built — read them in `workshop/memory.py` after you finish this TODO and notice how each one converts a different catalog view into the same `Fact` shape.

## How Facts Become Memories

After the four scanners run, the pre-built `write_facts()` function:

1. Computes `body_hash = sha256(fact.body)` — used for change detection.
2. Looks up an existing memory with the same `(kind, subject)` metadata.
3. **If absent** — calls `memory_client.add_memory(...)` (which embeds + inserts).
4. **If present and `body_hash` unchanged** — skips the embed call entirely.
5. **If present and `body_hash` changed** — updates the existing memory in place (same record id, so its links survive).
6. **After the facts are written** — `link_schema_facts()` connects them: every column fact and relationship fact links to its table fact with `supports`.
7. **`run_scan()` then records the run itself** — one row in `scan_history` (owner, objects scanned, facts written, JSON notes). That is *procedural* memory: queried by time and owner, not by meaning, so it lives in a regular table rather than the vector store.

The hash check is what makes hourly re-scans free. The vast majority of calls hash-check and skip; only schema changes trigger an embed. Re-running `link_schema_facts` is equally cheap: the store enforces one orientation per endpoint pair, so already-linked facts are counted and skipped.

Two store behaviours are worth knowing before you read the counters:

- **`store.list(...)` returns retired records too.** The lookup above takes the newest match (the
  list is ordered newest-first) and compares its `body_hash`; filtering by status is the caller's job
  — the same reason `search()` needs `include_invalid_results=False` when you want current truth only.
- **The same body can exist in more than one record.** With `MemoryExtractionConfig(extract_memories=True)`
  the extractor re-materialises a memory it rewrites and retires the record it came from, so a long-lived
  workspace accumulates historical records for one fact. The upsert above keeps *one current* record per
  `(kind, subject)`; Part 3 de-duplicates by body for exactly this reason.

> **Note** The first scan embeds every fact and makes an extraction round-trip per memory, so it takes minutes. Re-runs take seconds: every body hash matches and the loop skips the expensive path.

## Relations and Links (OAMP >= 26.8)

Facts do not exist in isolation. OAMP 26.8 stores a **directed relation** between two memories,
and the relation type decides what happens to the target:

| Type | Target after linking | Use for |
|---|---|---|
| `supersedes` | **retired** (`INVALID`) | a correction that replaces an earlier fact |
| `refines` | **retired** (`INVALID`) | a more precise version of the same fact |
| `duplicates` | **retired** (`INVALID`) | the same fact stored twice |
| `contradicts` | stays valid | conflicting evidence you want flagged, not resolved |
| `supports` | stays valid | corroborating evidence / structural detail |

Retired memories stop appearing in normal search but stay reachable through link traversal, so
nothing is lost — and "one orientation per endpoint pair" is enforced by the store, so re-linking is
safe.

```python
# Correction: write the new fact and retire the old one in a single call.
memory_client.add_memory(
    "The STRUCTURING threshold is now $12,500.",
    user_id=USER_ID, agent_id=AGENT_ID, metadata={"kind": "correction"},
    memory_id_to_link=old_memory_id, link_type="supersedes",
    autonomous_linking=False,        # deterministic; True lets the LLM pick extra links
)

# Traversal: one hop from each direct hit, in either direction.
results = memory_client.search(
    "STRUCTURING threshold", user_id=USER_ID,
    max_results=5, num_hops=1, max_linked_results=20,
)
for r in results:
    for relation, linked in (r.linked_results or []):
        print(relation.relation_type, linked.status, linked.content)
```

`num_hops` accepts 0–5. Pass `include_invalid_results=False` alongside a hop to read "current truth, plus its provenance" — retired memories stay one hop away, not in the current set. (Leaving the flag out can surface retired rows as direct hits, which is why the notebook passes it explicitly.)

The workshop uses links in four places:

- **The scanner graph (`run_scan`)** — `link_schema_facts()` links every column and relationship fact to its table fact with `supports`, so one hit on `FINANCE.TRANSACTIONS` brings its columns along.
- **`remember(supersedes=...)`** — the agent corrects a fact by memory id or by phrase; the old fact is retired (§4.3).
- **`link_memories(source, target, link_type)`** — connects two facts the agent already knows; `supports` / `contradicts` keep both current (§4.3).
- **`search_knowledge(follow_links=True)`** — the app's variant: adds one hop of linked context to every hit (`app/backend/agent/tools.py`). The same traversal is `memory_client.search(..., num_hops=1, max_linked_results=…)`.

The notebook links scanner facts (§2.3); relation types, hop traversal, memory types (`guideline` / `preference`) and retention (`ttl_days` → `EXPIRES_AT`) are reference material here, used by the app.

The right-side Memory Context pane renders relations as `→ relation` / `← relation` chips under each
memory, with retired ones struck through.

## Key Takeaways — Part 2

- **Don't hand-roll the memory schema.** OAMP gives you `memory`, `thread`, and `context_card`. Skipping it costs weeks of bookkeeping code that has nothing to do with the agent's actual job.
- **Catalog views are training data.** `ALL_TABLES + ALL_TAB_COLUMNS + ALL_CONSTRAINTS + V$SQL` mined into prose facts is how you teach an agent your schema without fine-tuning a model.
- **`body_hash` makes re-scans free.** The scanner only re-embeds facts whose underlying text changed. Hourly re-scans become viable when the dedup is content-based, not time-based.
- **Procedural memory is different.** `scan_history` (when/how the agent ran) is queried by time and owner, not by meaning — keep it as a regular indexed table, not an OAMP memory.
- **Links beat duplication.** Relation types carry lifecycle semantics: `supersedes`/`refines`/`duplicates` retire the target, `contradicts`/`supports` keep both. Retired facts disappear from normal search but stay one hop away, so corrections never lose history.

## Troubleshooting

**`ValueError: user already exists`** — OAMP's `add_user` and `add_agent` reject duplicate IDs. `register_user_and_agent` (§2.1) wraps these calls in `try/except ValueError`, but if you call them yourself, do the same.

**`ORA-00942: table or view does not exist`** — `ALL_TABLES` etc. are catalog views every user can read. If you see this, you're probably querying as a user without `SELECT_CATALOG_ROLE` (the setup cell granted it).

**Scanner returns 0 facts** — Check the `owner` argument is the schema name in uppercase. `ALL_TABLES.owner` is always uppercase even if you `CREATE USER demo`.
