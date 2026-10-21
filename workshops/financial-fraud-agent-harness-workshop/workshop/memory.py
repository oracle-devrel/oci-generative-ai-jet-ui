"""Part 2 helpers: schema scanners, fact upsert, link graph and scan history."""
import hashlib
import json
import uuid
from dataclasses import dataclass

import oracledb


@dataclass
class Fact:
    kind: str        # 'table' | 'column' | 'relationship' | 'query_pattern'
    subject: str     # e.g. 'FINANCE.TRANSACTIONS'
    body: str        # sentence the embedder will read
    metadata: dict


def register_user_and_agent(client, user_id, user_info, agent_id, agent_info):
    """Register the user and agent with OAMP; a repeat run is not an error."""
    for add, eid, info in ((client.add_user, user_id, user_info),
                           (client.add_agent, agent_id, agent_info)):
        try:
            add(eid, info)
        except ValueError as e:
            if "already exists" not in str(e):
                raise


TABLES_SQL = (
    "SELECT t.table_name, tc.comments, t.num_rows, t.last_analyzed "
    "  FROM all_tables t "
    "  LEFT JOIN all_tab_comments tc "
    "    ON tc.owner = t.owner AND tc.table_name = t.table_name "
    " WHERE t.owner = :owner "
    " ORDER BY t.table_name"
)


def scan_columns(conn, owner):
    sql = (
        "SELECT c.table_name, c.column_name, c.data_type, c.data_length, "
        "       c.nullable, cc.comments "
        "  FROM all_tab_columns c "
        "  LEFT JOIN all_col_comments cc "
        "    ON cc.owner = c.owner AND cc.table_name = c.table_name "
        "   AND cc.column_name = c.column_name "
        " WHERE c.owner = :owner "
        " ORDER BY c.table_name, c.column_id"
    )
    facts = []
    with conn.cursor() as cur:
        cur.execute(sql, owner=owner.upper())
        for table, col, dtype, dlen, nullable, comment in cur:
            dtype_str = dtype + (f"({dlen})" if dlen and dtype in ("VARCHAR2", "CHAR") else "")
            nullstr = "nullable" if nullable == "Y" else "NOT NULL"
            body = f"Column {owner}.{table}.{col} of type {dtype_str} ({nullstr})."
            if comment:
                body += f" Meaning: {comment}"
            facts.append(Fact("column", f"{owner}.{table}.{col}", body,
                              {"owner": owner, "table": table, "column": col,
                               "data_type": dtype, "nullable": nullable == "Y"}))
    return facts


def scan_relationships(conn, owner):
    sql = (
        "SELECT c.constraint_name, c.table_name, acc.column_name, "
        "       rc.table_name AS r_table, rcc.column_name AS r_column "
        "  FROM all_constraints c "
        "  JOIN all_cons_columns acc "
        "    ON acc.owner = c.owner AND acc.constraint_name = c.constraint_name "
        "  JOIN all_constraints rc "
        "    ON rc.owner = c.r_owner AND rc.constraint_name = c.r_constraint_name "
        "  JOIN all_cons_columns rcc "
        "    ON rcc.owner = rc.owner AND rcc.constraint_name = rc.constraint_name "
        "   AND rcc.position = acc.position "
        " WHERE c.owner = :owner AND c.constraint_type = 'R'"
    )
    facts = []
    with conn.cursor() as cur:
        cur.execute(sql, owner=owner.upper())
        for cname, tbl, col, r_tbl, r_col in cur:
            facts.append(Fact("relationship",
                              f"{owner}.{tbl}.{col}->{owner}.{r_tbl}.{r_col}",
                              f"Foreign key {cname}: {owner}.{tbl}.{col} references "
                              f"{owner}.{r_tbl}.{r_col}. Use this edge when joining the two tables.",
                              {"owner": owner, "child": tbl, "child_col": col,
                               "parent": r_tbl, "parent_col": r_col}))
    return facts


def scan_workload(conn, owner, limit=50):
    sql = (
        "SELECT sql_id, sql_fulltext, executions, rows_processed "
        "  FROM v$sql "
        " WHERE parsing_schema_name = :owner "
        "   AND command_type IN (3, 6, 7, 189) "
        "   AND rownum <= :lim "
        " ORDER BY executions DESC NULLS LAST"
    )
    facts = []
    with conn.cursor() as cur:
        try:
            cur.execute(sql, owner=owner.upper(), lim=limit)
            for sql_id, text, execs, rows_proc in cur:
                if text is None:
                    continue
                stmt = (text.read() if hasattr(text, "read") else str(text)).strip()
                if len(stmt) > 2000:
                    stmt = stmt[:2000] + " /* ...truncated */"
                facts.append(Fact("query_pattern", f"v$sql:{sql_id}",
                                  f"A SQL statement observed in the workload for {owner} "
                                  f"(executed {execs or 0} times, {rows_proc or 0} rows): {stmt}",
                                  {"owner": owner, "sql_id": sql_id,
                                   "executions": execs, "rows_processed": rows_proc}))
        except oracledb.DatabaseError as e:
            print(f"  (workload scan skipped: {e})")
    return facts


def body_hash(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:32]


def find_memory(client, user_id, agent_id, kind, subject):
    """Return the current memory for (kind, subject), or None."""
    rows = client._store.list("memory", user_id=user_id, agent_id=agent_id,
                              metadata_filter={"kind": kind, "subject": subject}, limit=1)
    return rows[0] if rows else None


def link_schema_facts(client, facts, user_id, agent_id, owner):
    """Link every column and relationship fact to its table fact with a `supports` relation."""
    store = client._store
    linked = already = 0

    def _id(kind, subject):
        m = find_memory(client, user_id, agent_id, kind, subject)
        return m.id if m else None

    tables = {f.subject: _id("table", f.subject) for f in facts if f.kind == "table"}
    for f in facts:
        if f.kind not in ("column", "relationship"):
            continue
        parent = f"{owner}.{f.metadata.get('table') or f.metadata.get('child')}"
        child_id, table_id = _id(f.kind, f.subject), tables.get(parent)
        if not child_id or not table_id:
            continue
        try:
            store.add_relations(source_record_ids=child_id, source_record_types="memory",
                                target_record_ids=table_id, target_record_types="memory",
                                relation_types="supports", metadata={})
            linked += 1
        except Exception:
            already += 1   # re-linking the same pair is a no-op
    return linked, already


def record_scan(conn, owner, scan_id, summary):
    """Log the scan in the scan_history table, creating it if setup did not."""
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM scan_history")
    except oracledb.DatabaseError:
        with conn.cursor() as cur:
            cur.execute(
                "CREATE TABLE scan_history ("
                "  scan_id          VARCHAR2(64) DEFAULT SYS_GUID() PRIMARY KEY,"
                "  target_owner     VARCHAR2(128) NOT NULL,"
                "  objects_scanned  NUMBER,"
                "  facts_written    NUMBER,"
                "  notes            VARCHAR2(4000),"
                "  started_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,"
                "  finished_at      TIMESTAMP)")
        conn.commit()
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO scan_history (scan_id, target_owner, objects_scanned, facts_written, "
            "                          notes, started_at, finished_at) "
            "VALUES (:s, :o, :objs, :facts, :notes, SYSTIMESTAMP, SYSTIMESTAMP)",
            s=scan_id, o=owner.upper(), objs=summary["facts_total"],
            facts=summary["new"] + summary["updated"], notes=json.dumps(summary),
        )
    conn.commit()


def upsert_facts(client, user_id, agent_id, facts, scan_id):
    """Add, update or skip each fact by (kind, subject) and body hash; returns (new, updated, skipped)."""
    new = updated = skipped = 0
    for f in facts:
        h = body_hash(f.body)
        existing = find_memory(client, user_id, agent_id, f.kind, f.subject)
        meta = {**f.metadata, "kind": f.kind, "subject": f.subject, "body_hash": h, "scan_id": scan_id}
        if not existing:
            client.add_memory(f.body, user_id=user_id, agent_id=agent_id, metadata=meta)
            new += 1
        elif (existing.metadata or {}).get("body_hash") == h:
            skipped += 1
        else:
            client.update_memory(existing.id, f.body, metadata=meta)
            updated += 1
    return new, updated, skipped


def finish_scan(client, conn, user_id, agent_id, owner, facts, counts, scan_id):
    """Link column and foreign-key facts to their tables, log the scan and return its summary."""
    links, already_linked = link_schema_facts(client, facts, user_id, agent_id, owner)
    new, updated, skipped = counts
    summary = {"facts_total": len(facts), "new": new, "updated": updated, "skipped": skipped,
               "links_created": links, "links_already_there": already_linked, "scan_id": scan_id}
    record_scan(conn, owner, scan_id, summary)
    return summary


class SchemaScanner:
    """Scan a schema into OAMP: the four scanners, `write_facts`, and `run_scan`.

    `scan_tables` is the notebook's TODO 3 function. `run_scan` calls `self.write_facts`, so
    replacing that attribute (Part 3 mirrors writes into the knowledge store) also affects `run_scan`.
    """

    def __init__(self, client, user_id, agent_id, scan_tables):
        self.client, self.user_id, self.agent_id, self.scan_tables = client, user_id, agent_id, scan_tables

    def scan_schema(self, conn, owner):
        return (self.scan_tables(conn, owner) + scan_columns(conn, owner)
                + scan_relationships(conn, owner) + scan_workload(conn, owner))

    def write_facts(self, facts, scan_id=None):
        return upsert_facts(self.client, self.user_id, self.agent_id, facts, scan_id or str(uuid.uuid4()))

    def run_scan(self, conn, owner):
        scan_id, facts = str(uuid.uuid4()), self.scan_schema(conn, owner)
        counts = self.write_facts(facts, scan_id=scan_id)
        return finish_scan(self.client, conn, self.user_id, self.agent_id, owner, facts, counts, scan_id)


def format_scan(summary):
    """One-line summary of a `run_scan` result."""
    return (f"scan: {summary['facts_total']} facts "
            f"({summary['new']} new, {summary['updated']} updated, {summary['skipped']} unchanged); "
            f"{summary['links_created']} links created, {summary['links_already_there']} already present")


def check_recall_memories(recall_memories, client, user_id, agent_id, subject, query):
    """Checkpoint for TODO 2: store one memory about `subject`, then recall it with `query`, which shares no words with it."""
    if not find_memory(client, user_id, agent_id, "column", subject):   # add once, even if re-run
        client.add_memory(
            "Table FINANCE.TRANSACTIONS column AMOUNT_CENTS: amounts are stored in USD CENTS, never dollars.",
            user_id=user_id, agent_id=agent_id, metadata={"kind": "column", "subject": subject})
    hits = recall_memories(query, k=3, kind="column")
    assert hits, ("❌ TODO 2: recall_memories returned nothing. Check that memory_client.search got user_id, "
                  "agent_id, record_types=['memory'] and max_results=k, and that you filled in both TODO lines.")
    assert all({"id", "kind", "subject", "body", "distance"} <= set(h) for h in hits), \
        "❌ TODO 2: each hit needs the keys id, kind, subject, body, distance."
    assert all(h["kind"] == "column" and h["body"] for h in hits), "❌ TODO 2: kind and body must come from the hit."
    assert any(h["subject"] == subject for h in hits), "❌ TODO 2: the stored memory did not come back."
    assert len(recall_memories(query, k=1, kind="column")) == 1, "❌ TODO 2: pass max_results=k to memory_client.search."
    assert recall_memories(query, k=3, kind="no_such_kind") == [], \
        '❌ TODO 2: set flt = {"kind": kind} when kind is given (else None) and pass metadata_filter=flt.'
    print(f"   top hit: d={hits[0]['distance']:.4f}  {hits[0]['subject']}")
    print("✅ TODO 2 passed: recalled the stored memory by meaning.")


def check_scan_tables(scan_tables, conn, owner):
    """Checkpoint for TODO 3: one table Fact per table in ALL_TABLES."""
    facts = scan_tables(conn, owner)
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM all_tables WHERE owner = :o", o=owner.upper())
        n_tables = cur.fetchone()[0]
    assert facts, "❌ TODO 3: _scan_tables returned no facts. Did you fill in the facts.append(Fact(...)) line?"
    assert all(isinstance(f, Fact) and f.kind == "table" for f in facts), "❌ TODO 3: append Fact objects whose kind is 'table'."
    assert len(facts) == n_tables, "❌ TODO 3: return one Fact per table in ALL_TABLES."
    txn = {f.subject: f for f in facts}.get(f"{owner}.TRANSACTIONS")
    assert txn, f"❌ TODO 3: subject must be f'{{owner}}.{{table}}', e.g. {owner}.TRANSACTIONS."
    assert txn.body.startswith(f"Table {owner}.TRANSACTIONS."), "❌ TODO 3: body must start with 'Table {owner}.{table}.'."
    assert {"owner", "table", "num_rows", "has_comment"} <= set(txn.metadata), "❌ TODO 3: metadata needs owner, table, num_rows, has_comment."
    assert ("Documented purpose:" in txn.body) == txn.metadata["has_comment"], "❌ TODO 3: add the purpose only when a comment exists."
    assert ("Approximate row count:" in txn.body) == (txn.metadata["num_rows"] is not None), "❌ TODO 3: append the row-count sentence only when num_rows is not None."
    assert not any("None" in f.body for f in facts), "❌ TODO 3: never write the word None into the body; skip the row-count sentence when num_rows is None."
    print(f"✅ TODO 3 passed: one table Fact per table in {owner}.")
