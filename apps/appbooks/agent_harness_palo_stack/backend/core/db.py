"""Database substrate for the appbook: a connection pool, idempotent harness setup,
the retrieval ladder, and the in-database scratch filesystem.

This is the same harness the notebook builds, ported to a long-lived service. It
connects to the existing AGENT schema and creates anything missing idempotently
(it never resets). The vector store is the maintained `langchain_oracledb` `OracleVS`
(same as the refactored notebook): in-database embeddings, library index + retriever
helpers. All embeddings are produced in-database by the loaded ONNX model.
"""
from __future__ import annotations

import json
import threading

import oracledb

from backend.config import settings

oracledb.defaults.fetch_lobs = False  # CLOB -> str, BLOB -> bytes

EMB = settings.embed_model
RERANK = settings.rerank_model
DIM = settings.vector_dim
VSTORE = "AGENT_VSTORE"

_pool: oracledb.ConnectionPool | None = None
_state = {"ready": False, "oracle": False, "rerank": False, "error": None}
_init_lock = threading.Lock()

# OracleVS store + its dedicated connection + a lock to serialise vector ops (single conn).
_store = None
_vs_conn = None
_kw_retriever = None
_vs_lock = threading.Lock()


# ── pool + helpers ────────────────────────────────────────────────────────
def _get_pool() -> oracledb.ConnectionPool:
    global _pool
    if _pool is None:
        _pool = oracledb.create_pool(
            user=settings.ora_user,
            password=settings.ora_password,
            dsn=settings.ora_dsn,
            min=2,
            max=8,
            increment=1,
        )
    return _pool


def q(sql: str, params=None):
    with _get_pool().acquire() as conn:
        cur = conn.cursor()
        try:
            cur.execute(sql, params or {})
            if cur.description is None:
                return []
            cols = [c[0] for c in cur.description]
            return [dict(zip(cols, r, strict=False)) for r in cur.fetchall()]
        finally:
            cur.close()


def x(sql: str, params=None, many=False):
    with _get_pool().acquire() as conn:
        cur = conn.cursor()
        try:
            cur.executemany(sql, params or []) if many else cur.execute(sql, params or {})
            conn.commit()
        finally:
            cur.close()


_IGNORE = (
    "ORA-00955",
    "ORA-01920",
    "ORA-00942",
    "ORA-01430",
    "ORA-02260",
    "ORA-01408",
    "ORA-00001",
    "ORA-29879",
    "ORA-29833",
    "ORA-12003",
    "ORA-00904",
)


def ddl(sql: str):
    try:
        x(sql)
        return True
    except Exception as e:
        if any(c in str(e) for c in _IGNORE):
            return False
        raise


def status() -> dict:
    return dict(_state)


# ── the OracleVS vector store (matches the refactored notebook) ────────────
def _build_store():
    """Create the OracleVS store + in-database embeddings + keyword retriever, and
    ensure the AGENT_VSTORE table and its HNSW + text indexes exist."""
    global _store, _vs_conn, _kw_retriever
    if _store is not None:
        return _store
    from langchain_oracledb.embeddings import OracleEmbeddings
    from langchain_oracledb.retrievers.text_search import (
        OracleTextSearchRetriever,
        create_text_index,
    )
    from langchain_oracledb.vectorstores import DistanceStrategy, OracleVS, oraclevs

    _vs_conn = oracledb.connect(
        user=settings.ora_user, password=settings.ora_password, dsn=settings.ora_dsn
    )
    emb = OracleEmbeddings(conn=_vs_conn, params={"provider": "database", "model": EMB})
    _store = OracleVS(
        client=_vs_conn,
        embedding_function=emb,
        table_name=VSTORE,
        distance_strategy=DistanceStrategy.COSINE,
    )

    # Ensure the table exists (OracleVS creates it on first write); bootstrap if missing.
    try:
        q(f"SELECT 1 FROM {VSTORE} WHERE rownum=1")
    except Exception:
        _store.add_texts(["__bootstrap__"], metadatas=[{"namespace": "__bootstrap"}])

    # Build the indexes with the library helpers (HNSW vector index + Oracle Text keyword index).
    try:
        oraclevs.drop_index_if_exists(_vs_conn, "AGENT_VSTORE_HNSW")
        oraclevs.create_index(
            _vs_conn,
            _store,
            params={
                "idx_name": "AGENT_VSTORE_HNSW",
                "idx_type": "HNSW",
                "accuracy": 95,
                "parallel": 4,
            },
        )
    except Exception:
        pass
    try:
        create_text_index(_vs_conn, idx_name="AGENT_VSTORE_TEXT", vector_store=_store)
    except Exception as e:
        if "ORA-00955" not in str(e):
            pass
    try:
        x(f"DELETE FROM {VSTORE} WHERE JSON_VALUE(metadata,'$.namespace')='__bootstrap'")
    except Exception:
        pass

    _kw_retriever = OracleTextSearchRetriever(
        vector_store=_store, k=30, fuzzy=True, return_scores=True
    )
    return _store


def _row(doc, score):
    """Adapt a langchain Document to the dict-row shape the rest of the app uses (CONTENT key)."""
    return {"ID": doc.id, "CONTENT": doc.page_content, "metadata": doc.metadata, "score": score}


# ── idempotent harness setup ──────────────────────────────────────────────
def initialize():
    with _init_lock:
        if _state["ready"]:
            return
        try:
            ver = q("SELECT banner FROM v$version WHERE rownum=1")
            _state["oracle"] = bool(ver)
            _state["rerank"] = bool(
                q("SELECT 1 FROM user_mining_models WHERE model_name=:m", {"m": RERANK})
            )
            _ensure_tables()
            _build_store()
            _seed_schema()
            scan_semantic_layer()
            _seed_knowledge()
            from backend.core import registries

            registries.register_default_tools()
            registries.seed_starter_skills()
            _state["ready"] = True
            _state["error"] = None
        except Exception as e:  # surface but keep serving the frontend
            _state["error"] = str(e).splitlines()[0]
            raise


def _ensure_tables():
    # NOTE: AGENT_VSTORE is owned by OracleVS (built in _build_store); we do not raw-create it here.
    ddl(
        """CREATE TABLE agent_scratch (
      path VARCHAR2(400) PRIMARY KEY, content BLOB, is_dir CHAR(1) DEFAULT 'N',
      promoted CHAR(1) DEFAULT 'N', updated_at TIMESTAMP DEFAULT SYSTIMESTAMP) LOB (content) STORE AS SECUREFILE"""
    )
    ddl(
        f"""CREATE TABLE agent_workflow (
      id RAW(16) DEFAULT SYS_GUID() PRIMARY KEY, intent VARCHAR2(400), steps CLOB,
      tools_used VARCHAR2(1000), occurrences NUMBER DEFAULT 1, promoted CHAR(1) DEFAULT 'N',
      embedding VECTOR({DIM}, FLOAT32), created_at TIMESTAMP DEFAULT SYSTIMESTAMP,
      last_seen TIMESTAMP DEFAULT SYSTIMESTAMP)"""
    )
    ddl(
        f"""CREATE TABLE agent_tools (
      name VARCHAR2(120) PRIMARY KEY, description VARCHAR2(600), category VARCHAR2(60),
      tool_schema JSON, embedding VECTOR({DIM}, FLOAT32), created_at TIMESTAMP DEFAULT SYSTIMESTAMP)"""
    )
    ddl(
        """CREATE VECTOR INDEX agent_tools_hnsw ON agent_tools (embedding)
      ORGANIZATION INMEMORY NEIGHBOR GRAPH DISTANCE COSINE WITH TARGET ACCURACY 95"""
    )
    ddl(
        f"""CREATE TABLE agent_skills (
      name VARCHAR2(120) PRIMARY KEY, description VARCHAR2(600), sha VARCHAR2(64), source_url VARCHAR2(600),
      skill_md CLOB, tools_used VARCHAR2(600), source_workflow_id RAW(16), embedding VECTOR({DIM}, FLOAT32),
      created_at TIMESTAMP DEFAULT SYSTIMESTAMP, updated_at TIMESTAMP DEFAULT SYSTIMESTAMP)"""
    )
    ddl(
        """CREATE VECTOR INDEX agent_skills_hnsw ON agent_skills (embedding)
      ORGANIZATION INMEMORY NEIGHBOR GRAPH DISTANCE COSINE WITH TARGET ACCURACY 95"""
    )
    ddl(
        """CREATE TABLE agent_automations (
      name VARCHAR2(120) PRIMARY KEY, description VARCHAR2(600), artifact VARCHAR2(120),
      job_name VARCHAR2(120), cadence_hours NUMBER, select_sql CLOB, created_at TIMESTAMP DEFAULT SYSTIMESTAMP)"""
    )
    ddl(
        f"""CREATE TABLE agent_tool_log (
      id RAW(16) DEFAULT SYS_GUID() PRIMARY KEY, tool VARCHAR2(120), payload CLOB,
      embedding VECTOR({DIM}, FLOAT32), created_at TIMESTAMP DEFAULT SYSTIMESTAMP)"""
    )


def _seed_schema():
    for d in [
        """CREATE TABLE customers (customer_id NUMBER PRIMARY KEY, name VARCHAR2(100), email VARCHAR2(120),
            country VARCHAR2(40), segment VARCHAR2(20), signup_date DATE)""",
        """CREATE TABLE products (product_id NUMBER PRIMARY KEY, name VARCHAR2(100), category VARCHAR2(40),
            unit_price NUMBER(10,2), unit_cost NUMBER(10,2))""",
        """CREATE TABLE orders (order_id NUMBER PRIMARY KEY, customer_id NUMBER REFERENCES customers,
            order_date DATE, status VARCHAR2(20), channel VARCHAR2(20))""",
        """CREATE TABLE order_items (order_item_id NUMBER PRIMARY KEY, order_id NUMBER REFERENCES orders,
            product_id NUMBER REFERENCES products, quantity NUMBER, unit_price NUMBER(10,2),
            discount NUMBER(5,2) DEFAULT 0)""",
    ]:
        ddl(d)
    if q("SELECT COUNT(*) n FROM customers")[0]["N"] == 0:
        import random

        rnd = random.Random(42)
        cats, chans, segs = (
            ["Outdoors", "Electronics", "Home", "Apparel"],
            ["web", "store", "partner"],
            ["consumer", "smb", "enterprise"],
        )
        x(
            "INSERT INTO customers VALUES (:1,:2,:3,:4,:5, SYSDATE - :6)",
            [
                (
                    i,
                    f"Customer {i}",
                    f"c{i}@example.com",
                    rnd.choice(["US", "GB", "DE", "FR"]),
                    rnd.choice(segs),
                    rnd.randint(30, 900),
                )
                for i in range(1, 61)
            ],
            many=True,
        )
        x(
            "INSERT INTO products VALUES (:1,:2,:3,:4,:5)",
            [
                (
                    i,
                    f"Product {i}",
                    rnd.choice(cats),
                    round(rnd.uniform(10, 400), 2),
                    round(rnd.uniform(5, 200), 2),
                )
                for i in range(1, 41)
            ],
            many=True,
        )
        oid, items = 1, []
        for _ in range(400):
            x(
                "INSERT INTO orders VALUES (:oid, :cust, SYSDATE - :age, :st, :ch)",
                {
                    "oid": oid,
                    "cust": rnd.randint(1, 60),
                    "age": rnd.randint(0, 180),
                    "st": rnd.choice(["paid", "paid", "paid", "refunded"]),
                    "ch": rnd.choice(chans),
                },
            )
            for _ in range(rnd.randint(1, 4)):
                items.append(
                    (
                        len(items) + 1,
                        oid,
                        rnd.randint(1, 40),
                        rnd.randint(1, 5),
                        round(rnd.uniform(10, 400), 2),
                        rnd.choice([0, 0, 0, 5, 10]),
                    )
                )
            oid += 1
        x("INSERT INTO order_items VALUES (:1,:2,:3,:4,:5,:6)", items, many=True)
    ddl(
        """CREATE OR REPLACE VIEW v_revenue AS
      SELECT o.order_id, o.order_date, o.channel, c.segment, c.country, p.category, oi.quantity,
             (oi.unit_price * oi.quantity) * (1 - NVL(oi.discount,0)/100) AS net_revenue
      FROM orders o JOIN order_items oi ON oi.order_id=o.order_id
                    JOIN products p ON p.product_id=oi.product_id
                    JOIN customers c ON c.customer_id=o.customer_id
      WHERE o.status='paid' """
    )
    try:
        x(
            "COMMENT ON COLUMN v_revenue.net_revenue IS 'Net paid revenue per line = price * qty * (1-discount)'"
        )
        x("COMMENT ON TABLE orders IS 'One row per customer order; status is paid or refunded'")
        x(
            "COMMENT ON COLUMN order_items.discount IS 'Percentage discount applied to the line (0-100)'"
        )
    except Exception:
        pass


# ── encoding (write path) — via OracleVS ──────────────────────────────────
def add_texts(texts, metadatas=None, namespace="knowledge"):
    metadatas = metadatas or [{} for _ in texts]
    rows = [
        {**(m or {}), "namespace": namespace} for m in metadatas
    ]  # distinct dicts; namespace in metadata
    with _vs_lock:
        _build_store().add_texts(list(texts), metadatas=rows)
    return len(texts)


def embed_dims(text: str) -> int:
    r = q(f"SELECT VECTOR_EMBEDDING({EMB} USING :t AS DATA) v FROM dual", {"t": text})
    v = r[0]["V"] if r else None
    return len(v) if v is not None else 0


def embedding_preview(text: str, n: int = 8):
    r = q(f"SELECT VECTOR_EMBEDDING({EMB} USING :t AS DATA) v FROM dual", {"t": text})
    v = list(r[0]["V"]) if r and r[0]["V"] is not None else []
    return {"dims": len(v), "head": [round(float(x), 4) for x in v[:n]]}


# ── retrieval ladder (read path) — via the library retrievers ─────────────
def kw_search(query, namespace="knowledge", k=5):
    with _vs_lock:
        _build_store()
        docs = _kw_retriever.invoke(query or "")
    if namespace:
        docs = [d for d in docs if d.metadata.get("namespace") == namespace]
    return [_row(d, d.metadata.get("score")) for d in docs[:k]]


def vec_search(query, namespace="knowledge", k=5):
    flt = {"namespace": namespace} if namespace else None
    with _vs_lock:
        pairs = _build_store().similarity_search_with_score(query, k=k, filter=flt)
    return [dict(_row(d, dist), dist=dist) for d, dist in pairs]


def hybrid_search(query, namespace="knowledge", k=5, pool=20, c=60):
    v, t = vec_search(query, namespace, pool), kw_search(query, namespace, pool)
    scores, store = {}, {}
    for rank, r in enumerate(v):
        rid = r["ID"]
        store[rid] = r
        scores[rid] = scores.get(rid, 0) + 1.0 / (c + rank + 1)
    for rank, r in enumerate(t):
        rid = r["ID"]
        store[rid] = r
        scores[rid] = scores.get(rid, 0) + 1.0 / (c + rank + 1)
    ranked = sorted(scores, key=scores.get, reverse=True)[:k]
    return [dict(store[rid], rrf=round(scores[rid], 4)) for rid in ranked]


def rerank(query, candidates, k=5):
    if not _state["rerank"] or not candidates:
        return [dict(c, rerank_score=None) for c in candidates[:k]]
    docs = [str(c["CONTENT"])[:2000] for c in candidates]
    try:
        rows = q(
            f"""SELECT t.idx AS idx,
                 PREDICTION({RERANK} USING (:q || ' [SEP] ' || t.doc) AS DATA) AS score
                 FROM JSON_TABLE(:docs, '$[*]' COLUMNS (idx FOR ORDINALITY, doc VARCHAR2(4000) PATH '$')) t
                 ORDER BY score DESC""",
            {"q": query, "docs": json.dumps(docs)},
        )
        return [
            dict(candidates[r["IDX"] - 1], rerank_score=round(float(r["SCORE"]), 3))
            for r in rows[:k]
        ]
    except Exception:
        return [dict(c, rerank_score=None) for c in candidates[:k]]


def retrieve(query, technique="hybrid", namespace="knowledge", k=5):
    if technique == "keyword":
        return kw_search(query, namespace, k)
    if technique == "vector":
        return vec_search(query, namespace, k)
    hits = hybrid_search(query, namespace, k=max(k, 8))
    if technique == "rerank":
        return rerank(query, hits, k)
    return hits[:k]


# ── semantic catalog ──────────────────────────────────────────────────────
def scan_semantic_layer():
    facts = []
    cols = q(
        """SELECT tc.table_name, tc.column_name, tc.data_type, cc.comments
        FROM user_tab_columns tc
        LEFT JOIN user_col_comments cc ON cc.table_name=tc.table_name AND cc.column_name=tc.column_name
        WHERE tc.table_name IN ('CUSTOMERS','PRODUCTS','ORDERS','ORDER_ITEMS')"""
    )
    for c in cols:
        body = f"{c['TABLE_NAME']}.{c['COLUMN_NAME']} ({c['DATA_TYPE']})"
        if c["COMMENTS"]:
            body += f" -- {c['COMMENTS']}"
        facts.append((f"col:{c['TABLE_NAME']}.{c['COLUMN_NAME']}", body, "column"))
    for f in q(
        """SELECT a.table_name, a.column_name, c_pk.table_name AS ref_table
        FROM user_cons_columns a
        JOIN user_constraints c ON a.constraint_name=c.constraint_name AND c.constraint_type='R'
        JOIN user_constraints c_pk ON c.r_constraint_name=c_pk.constraint_name"""
    ):
        facts.append(
            (
                f"fk:{f['TABLE_NAME']}.{f['COLUMN_NAME']}",
                f"{f['TABLE_NAME']}.{f['COLUMN_NAME']} joins to {f['REF_TABLE']}",
                "fk",
            )
        )
    try:
        x(
            f"""DELETE FROM {VSTORE} WHERE JSON_VALUE(metadata,'$.namespace')='semantic'
              AND JSON_VALUE(metadata,'$.kind')='catalog'"""
        )
    except Exception:
        pass
    add_texts(
        [b for _, b, _ in facts],
        [{"kind": "catalog", "subject": s, "ftype": t} for s, b, t in facts],
        namespace="semantic",
    )
    return len(facts)


def semantic_search(query, k=6):
    return vec_search(query, namespace="semantic", k=k)


def _seed_knowledge():
    n = q(f"SELECT COUNT(*) n FROM {VSTORE} WHERE JSON_VALUE(metadata,'$.namespace')='knowledge'")[
        0
    ]["N"]
    if n > 0:
        return
    add_texts(
        [
            "The Outdoors category drove Q3 revenue growth.",
            "Supplier concentration is the top operational risk this quarter.",
            "A dual-sourcing decision for Outdoors is targeted for Q1.",
            "Customer churn rises sharply when delivery exceeds five days.",
            "Returns spike in the Apparel category right after the holidays.",
            "Enterprise-segment customers have the highest average order value.",
        ],
        [{"src": "kb"} for _ in range(6)],
        namespace="knowledge",
    )
