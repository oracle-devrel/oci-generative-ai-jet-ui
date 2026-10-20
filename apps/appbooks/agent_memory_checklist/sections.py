"""The fifteen checklist sections. Each has a `without` run (the failure mode) and a `with` run (Oracle AI Database).

Every run returns the same shape, so the browser can render any of them:
    summary, verdict (bad | good | info), status (ok | skipped), context (what the agent would see),
    rows (a table), sql, metrics, log, note, question, user, extra.
"""
from __future__ import annotations

import ast
import base64
import json
import operator
import re
import time
import uuid
from datetime import UTC, datetime
from typing import Literal

import claude
import numpy as np
import oracledb
from lab import (
    INSERT_MEMORY,
    LOCK,
    MODEL,
    RERANKER,
    SCHEMA,
    STATE,
    embed,
    first_line,
    memory_binds,
    owner,
    q,
    session,
    x,
)

TICKET = re.compile(r"\b[A-Z]{2,}-\d+\b")
STOPWORDS = {
    "what",
    "with",
    "that",
    "this",
    "from",
    "have",
    "after",
    "afterwards",
    "about",
    "which",
    "were",
    "when",
    "does",
}


def result(summary, verdict="info", status="ok", **kw):
    return {"summary": summary, "verdict": verdict, "status": status, **kw}


def context(rows, *extra):
    return [
        {
            "memory_id": r["memory_id"],
            "user_id": r.get("user_id"),
            "content": r["content"],
            **{k: r[k] for k in extra if k in r},
        }
        for r in rows
    ]


def ms_since(start):
    return (time.perf_counter() - start) * 1000


def proved(sid, evidence):
    STATE["results"][sid] = ("proved", evidence)


# ----------------------------------------------------------------------------------------------- recall helpers
VECTOR_SQL = f"""SELECT memory_id, user_id, memory_type,
       ROUND(1 - VECTOR_DISTANCE(embedding, VECTOR_EMBEDDING({MODEL} USING :q AS data), COSINE), 4) AS score, content
FROM memories
WHERE valid_to IS NULL {{where}}
ORDER BY VECTOR_DISTANCE(embedding, VECTOR_EMBEDDING({MODEL} USING :q AS data), COSINE)
FETCH APPROX FIRST {{k}} ROWS ONLY"""

BOUND_VECTOR_SQL = f"""SELECT memory_id, user_id, content FROM {SCHEMA}.memories WHERE valid_to IS NULL
ORDER BY VECTOR_DISTANCE(embedding, :qv, COSINE) FETCH APPROX FIRST {{k}} ROWS ONLY"""


def vector_recall(question, k=5, where="", binds=None):
    sql = VECTOR_SQL.format(where=where, k=int(k))
    return sql, q(sql, {"q": question, **(binds or {})})


def sync_text():
    """Index any new or changed rows for keyword and hybrid search, in the owner session (see lab.build)."""
    x("BEGIN CTX_DDL.SYNC_INDEX('memories_hybrid_idx'); END;")


def lexical(expr, k=5):
    sync_text()
    return q(LEXICAL_SQL, {"expr": expr, "k": k})


def contains_expr(text):
    """A question as an Oracle Text expression: content words, each escaped with braces, accumulated."""
    words = [
        w
        for w in re.findall(r"[A-Za-z0-9][A-Za-z0-9\-]*", text)
        if len(w) > 3 and w.lower() not in STOPWORDS
    ]
    return " ACCUM ".join("{%s}" % w for w in words)


LEXICAL_SQL = """SELECT memory_id, user_id, SCORE(1) AS score, content FROM memories
WHERE CONTAINS(content, :expr, 1) > 0 AND valid_to IS NULL
ORDER BY SCORE(1) DESC, memory_id FETCH FIRST :k ROWS ONLY"""

HYBRID_SQL = """SELECT m.memory_id, m.user_id, h.score, h.vector_rank, h.text_rank, m.content
FROM JSON_TABLE(DBMS_HYBRID_VECTOR.SEARCH(JSON(:spec)), '$[*]'
       COLUMNS (rid VARCHAR2(30) PATH '$.rowid', score NUMBER PATH '$.score',
                vector_rank NUMBER PATH '$.vector_rank', text_rank NUMBER PATH '$.text_rank')) h
JOIN memories m ON m.rowid = CHARTOROWID(h.rid)
WHERE m.valid_to IS NULL
ORDER BY h.score DESC"""


def hybrid_spec(question, k=5, fusion="UNION", scorer="rrf"):
    return {
        "hybrid_index_name": "memories_hybrid_idx",
        "search_scorer": scorer,
        "search_fusion": fusion,
        "vector": {"search_text": question, "search_mode": "DOCUMENT", "aggregator": "MAX"},
        "text": {"contains": contains_expr(question)},
        "return": {"values": ["rowid", "score", "vector_rank", "text_rank"], "topN": k},
    }


def hybrid_recall(question, k=5, fusion="UNION", scorer="rrf"):
    sync_text()
    spec = hybrid_spec(question, k, fusion, scorer)
    return spec, q(HYBRID_SQL, {"spec": json.dumps(spec)})


# ----------------------------------------------------------------------------------------------- §1 shapes
def s1_without(p):
    stores, held, log = (
        ["document store", "vector store", "relational store", "graph store"],
        [],
        [],
    )
    for name in stores:
        if name == "graph store":
            log.append("graph store: connection reset, the write failed")
            break
        held.append(name)
        log.append(f"{name}: write committed on its own")
    rows = [{"store": s, "holds the new memory": "yes" if s in held else "no"} for s in stores]
    return result(
        f"{len(held)} of 4 stores hold the new memory, and nothing can roll them back together",
        "bad",
        rows=rows,
        log=log,
        note="Simulated: four in-process stand-ins for four products, four separate writes.",
    )


def s1_with(p):
    cols = q(
        "SELECT column_name, data_type FROM user_tab_columns WHERE table_name = 'MEMORIES' ORDER BY column_id"
    )
    binds = memory_binds(
        "mem_demo",
        "user_ada",
        "agent_planner",
        "semantic",
        0.5,
        datetime.now(UTC),
        "cairn",
        "demo",
        "A memory written in one transaction: row, CLOB, JSON and vector together.",
    )
    log, conn = [], owner()
    try:
        with conn.cursor() as cur:
            cur.setinputsizes(metadata=oracledb.DB_TYPE_JSON)
            cur.execute(INSERT_MEMORY, binds)
        inside = q(
            """SELECT memory_id, JSON_VALUE(metadata, '$.project') AS project, DBMS_LOB.GETLENGTH(content) AS clob_chars,
                             VECTOR_DIMENSION_COUNT(embedding) AS vector_dims FROM memories WHERE memory_id = 'mem_demo'"""
        )[0]
        log.append(f"inside the transaction: {inside}")
        x("INSERT INTO memory_mentions VALUES ('mem_demo', 'ent_does_not_exist')")
        conn.commit()
    except oracledb.DatabaseError as e:
        conn.rollback()
        log.append(f"the graph edge failed: {first_line(e)} → ROLLBACK")
    left = q("SELECT COUNT(*) AS n FROM memories WHERE memory_id = 'mem_demo'")[0]["n"]
    proved(
        "s1",
        "relational, CLOB, JSON and VECTOR columns in one table; one rollback undid all of them",
    )
    return result(
        f"One table holds every shape, and one rollback undid the row, CLOB, JSON and vector together "
        f"({left} partial rows left)",
        "good",
        rows=cols,
        log=log,
        sql=INSERT_MEMORY.strip(),
    )


# ----------------------------------------------------------------------------------------------- §2 embedding
HF_MODEL = "sentence-transformers/all-MiniLM-L12-v2"
DEFAULT_TEXT = (
    "Decision: the team wants a standalone vector database as the agent memory store for Cairn."
)


def median_ms(fn, n=5):
    fn()  # warm-up, not timed
    times = []
    for _ in range(n):
        start = time.perf_counter()
        value = fn()
        times.append(ms_since(start))
    return float(np.median(times)), value


def s2_without(p):
    text = p.get("text") or DEFAULT_TEXT
    try:
        from huggingface_hub import InferenceClient, get_token

        if not get_token():
            return result(
                "Skipped: set HF_TOKEN to race the same model over the network.", status="skipped"
            )
        hf = InferenceClient(provider="hf-inference")
        ms, vec = median_ms(
            lambda: np.asarray(
                hf.feature_extraction(text, model=HF_MODEL), dtype=np.float32
            ).ravel()
        )
    except Exception as e:
        return result(f"Skipped: {str(e).strip().splitlines()[-1][:200]}", status="skipped")
    STATE["remote"] = {"text": text, "vec": vec, "ms": ms}
    return result(
        f"The same model over the network: median {ms:.0f} ms a call, and the memory text left your system",
        "bad",
        metrics=[
            ["median per call", f"{ms:.0f} ms"],
            ["bytes sent per call", f"{len(text.encode()):,}"],
            ["dimensions", len(vec)],
        ],
        extra={"vector": [round(float(v), 4) for v in vec[:8]]},
        note=f"Hugging Face Inference, {HF_MODEL}: one warm-up call, then the median of five.",
    )


def s2_with(p):
    text = p.get("text") or DEFAULT_TEXT
    ms, vec = median_ms(lambda: embed(text))
    metrics = [
        ["median per call", f"{ms:.1f} ms"],
        ["bytes sent out", "0"],
        ["dimensions", len(vec)],
    ]
    remote = STATE.get("remote")
    if remote and remote["text"] == text:
        a, b = np.asarray(vec), remote["vec"]
        metrics += [
            ["faster than the network", f"{remote['ms'] / ms:.0f}×"],
            [
                "cosine vs the network vector",
                f"{a @ b / (np.linalg.norm(a) * np.linalg.norm(b)):.4f}",
            ],
        ]
    proved("s2", f"VECTOR_EMBEDDING in the database, median {ms:.1f} ms, nothing sent out")
    return result(
        f"VECTOR_EMBEDDING in the database: median {ms:.1f} ms a call, and nothing left the database",
        "good",
        metrics=metrics,
        extra={"vector": [round(v, 4) for v in vec[:8]]},
        sql=f"SELECT VECTOR_EMBEDDING({MODEL} USING :text AS data) FROM dual",
    )


# ----------------------------------------------------------------------------------------------- §3 vector recall
Q3 = "How do I undo a faulty save into the assistant's knowledge base?"


def words(text):
    return [
        w.lower()
        for w in re.findall(r"[A-Za-z][A-Za-z\-]*", text)
        if len(w) > 3 and w.lower() not in STOPWORDS | {"into"}
    ]


def s3_without(p):
    question = p.get("question") or Q3
    terms = words(question)
    expr = " ACCUM ".join(
        f"${t}" if t.isalpha() else "{%s}" % t for t in terms
    )  # $ = stem, like a search engine
    rows = lexical(expr) if terms else []
    _, best = vector_recall(question, k=1)
    missed = bool(best) and best[0]["memory_id"] not in {r["memory_id"] for r in rows}
    summary = (
        f"Keyword search found {len(rows)} {'memory that shares' if len(rows) == 1 else 'memories that share'} "
        "a word with the question"
    )
    if missed:
        summary += f", and missed the closest one by meaning ({best[0]['memory_id']})"
    return result(
        summary,
        "bad" if missed else "info",
        context=context(rows, "score"),
        question=question,
        sql=LEXICAL_SQL,
        log=[
            f"CONTAINS expression: {expr or '(no searchable words)'}  ($ stems each word: 'saves' matches 'save')"
        ],
        note="Keyword search can only find memories that use the question's words. People rarely do.",
    )


def s3_with(p):
    question = p.get("question") or Q3
    sql, rows = vector_recall(question)
    common = sorted(set(words(question)) & set(words(rows[0]["content"]))) if rows else []
    proved(
        "s3",
        f"{STATE['index_kind']} index + FETCH APPROX FIRST 5; top hit {rows[0]['memory_id']} by meaning",
    )
    return result(
        f"Vector search by meaning: the top hit, {rows[0]['memory_id']}, shares "
        f"{', '.join(common) if common else 'no words'} with the question",
        "good",
        context=context(rows, "score"),
        question=question,
        sql=sql,
        metrics=[
            ["index", STATE["index_kind"]],
            ["words shared with the top hit", len(common)],
            ["rows returned", len(rows)],
        ],
    )


# ----------------------------------------------------------------------------------------------- §4 lexical recall
Q4 = "What happened with INC-4812?"


def s4_without(p):
    question = p.get("question") or Q4
    sql, rows = vector_recall(question, k=20)
    ids = TICKET.findall(question)
    ranks = {
        i: next(
            (n for n, r in enumerate(rows, 1) if i in r["content"] and r["content"].startswith(i)),
            None,
        )
        for i in ids
    }
    found = all(r and r <= 5 for r in ranks.values()) if ids else True
    where = ", ".join(
        f"{i} ranks #{r}" if r else f"{i} not in the top 20" for i, r in ranks.items()
    )
    return result(
        f"Vector search only: the exact ticket {'is' if found else 'is not'} in the top five ({where})",
        "info" if found else "bad",
        context=context(rows[:5], "score"),
        question=question,
        sql=sql,
    )


def s4_with(p):
    question = p.get("question") or Q4
    ids = TICKET.findall(question)
    expr = " OR ".join("{%s}" % i for i in ids) or contains_expr(question)
    rows = lexical(expr)
    log = [f"CONTAINS expression: {expr}"]
    for i in ids:
        trap = lexical(i)
        log.append(
            f"the trap, unescaped '{i}' (read as {i.replace('-', ' MINUS ')}): {', '.join(r['memory_id'] for r in trap) or 'nothing'}"
        )
    proved("s4", f"CONTAINS('{expr}') recalled the exact ticket")
    return result(
        f"Oracle Text: {len(rows)} memories mention the exact identifier",
        "good",
        context=context(rows, "score"),
        question=question,
        sql=LEXICAL_SQL,
        log=log,
        note="In Oracle Text '-' is the MINUS operator, so identifiers go in braces.",
    )


# ----------------------------------------------------------------------------------------------- §5 hybrid
Q5 = "what happened with INC-4812 and what changed in Comet recall afterwards"


def s5_without(p):
    question = p.get("question") or Q5
    _, vec = vector_recall(question, k=10)
    txt = lexical(contains_expr(question), k=10)
    fused = {}
    for ranked in (vec, txt):  # reciprocal rank fusion, written by hand
        for rank, r in enumerate(ranked, 1):
            fused.setdefault(r["memory_id"], dict(r, score=0.0))["score"] += 1 / (60 + rank)
    top = sorted(fused.values(), key=lambda r: -r["score"])[:5]
    for r in top:
        r["score"] = round(r["score"], 4)
    return result(
        "Two queries, two result lists, and a fusion function in application code",
        "bad",
        context=context(top, "score"),
        question=question,
        log=[
            f"vector list: {', '.join(r['memory_id'] for r in vec)}",
            f"text list: {', '.join(r['memory_id'] for r in txt)}",
            "fused in Python: score = Σ 1 / (60 + rank)",
        ],
        note="Every change to the fusion is a code change, and two indexes drift apart as the data changes.",
    )


def s5_with(p):
    question = p.get("question") or Q5
    spec, rows = hybrid_recall(
        question, fusion=p.get("fusion") or "UNION", scorer=p.get("scorer") or "rrf"
    )
    proved(
        "s5",
        f"DBMS_HYBRID_VECTOR.SEARCH ({spec['search_fusion']}, {spec['search_scorer'].upper()}) in one call",
    )
    return result(
        f"One hybrid vector index, one call: {spec['search_fusion']} fusion with {spec['search_scorer'].upper()} scoring",
        "good",
        context=context(rows, "score", "vector_rank", "text_rank"),
        question=question,
        sql=HYBRID_SQL,
        extra={"spec": spec},
    )


# ----------------------------------------------------------------------------------------------- §6 filtered recall
Q6 = "How do we roll back a bad memory write?"


def s6_params(p):
    return (
        p.get("user") or "user_cy",
        p.get("memory_type") or "procedural",
        p.get("since") or "2026-09-01",
    )


def s6_without(p):
    user, mtype, since = s6_params(p)
    question = p.get("question") or Q6
    sql, top5 = vector_recall(question, k=5)
    after = datetime.fromisoformat(since).replace(tzinfo=UTC)
    kept = [r for r in top5 if r["user_id"] == user and r["memory_type"] == mtype]
    kept = [
        r
        for r in kept
        if q("SELECT created_at FROM memories WHERE memory_id = :m", {"m": r["memory_id"]})[0][
            "created_at"
        ]
        >= after
    ]
    return result(
        f"Post-filter: the top five belong to {sorted({r['user_id'] for r in top5})}; {len(kept)} survive the filter",
        "bad" if not kept else "info",
        context=context(kept, "score"),
        question=question,
        user=user,
        sql=sql,
        log=[
            f"top five before filtering: {', '.join(r['memory_id'] + ' (' + r['user_id'] + ')' for r in top5)}"
        ],
    )


def plan_ops(hint=""):
    x(
        f"""EXPLAIN PLAN FOR SELECT {hint} memory_id FROM memories
          WHERE valid_to IS NULL AND user_id = 'user_cy' AND memory_type = 'procedural'
          ORDER BY VECTOR_DISTANCE(embedding, VECTOR_EMBEDDING({MODEL} USING 'x' AS data), COSINE)
          FETCH APPROX FIRST 5 ROWS ONLY"""
    )
    rows = q("SELECT plan_table_output AS p FROM TABLE(DBMS_XPLAN.DISPLAY(NULL, NULL, 'BASIC'))")
    return [
        r["p"].split("|")[2].strip()
        for r in rows
        if r["p"].startswith("|") and "Operation" not in r["p"]
    ]


def s6_with(p):
    user, mtype, since = s6_params(p)
    question = p.get("question") or Q6
    where = """AND user_id = :user_id AND memory_type = :memory_type AND created_at >= :since
              AND JSON_VALUE(metadata, '$.project') IN ('cairn', 'beacon', 'comet')"""
    sql, rows = vector_recall(
        question,
        k=5,
        where=where,
        binds={
            "user_id": user,
            "memory_type": mtype,
            "since": datetime.fromisoformat(since).replace(tzinfo=UTC),
        },
    )
    forced = plan_ops("/*+ VECTOR_INDEX_TRANSFORM(memories memories_hnsw_idx) */")
    proved("s6", f"filter inside the search returned {len(rows)} memories")
    return result(
        f"The filter inside the search: {len(rows)} of {user}'s {mtype} memories, ranked by meaning",
        "good",
        context=context(rows, "score"),
        question=question,
        user=user,
        sql=sql,
        log=[f"optimiser's plan: {' → '.join(plan_ops())}", f"index forced: {' → '.join(forced)}"],
    )


# ----------------------------------------------------------------------------------------------- §7 reranking
RERANK_SQL = f"""SELECT memory_id, user_id, ROUND(PREDICTION({RERANKER} USING (:q || ' ¶ ' || content) AS DATA), 2) AS relevance, content
FROM memories
WHERE memory_id IN (SELECT id FROM JSON_TABLE(:ids, '$[*]' COLUMNS (id VARCHAR2(40) PATH '$')))
ORDER BY relevance DESC FETCH FIRST 5 ROWS ONLY"""


def s7_without(p):
    question = p.get("question") or Q5
    _, rows = hybrid_recall(question, k=10)
    return result(
        "Fused order as it comes: whatever the fusion scored highest goes first",
        "info",
        context=context(rows[:5], "score"),
        question=question,
        note="The alternative is a reranking API, which sends the candidates out of the database again.",
    )


def s7_with(p):
    question = p.get("question") or Q5
    if not STATE.get("reranker"):
        STATE["results"]["s7"] = ("skipped", "no reranker model loaded")
        return result(
            "Skipped: no reranker model is loaded. Export it with the notebook's §7, then rebuild the lab.",
            status="skipped",
        )
    _, candidates = hybrid_recall(question, k=10)
    rows = q(RERANK_SQL, {"q": question, "ids": json.dumps([r["memory_id"] for r in candidates])})
    proved("s7", f"PREDICTION over an ONNX cross-encoder; top hit {rows[0]['memory_id']}")
    return result(
        "A cross-encoder scored each candidate against the question, inside the database",
        "good",
        context=context(rows, "relevance"),
        question=question,
        sql=RERANK_SQL,
        log=[f"candidates (fused order): {', '.join(r['memory_id'] for r in candidates)}"],
    )


# ----------------------------------------------------------------------------------------------- §8 graph recall
Q8 = "Why is Cairn over its cloud budget, and what did we decide to do about it?"
GRAPH_SQL = f"""WITH seed AS (
    SELECT memory_id FROM memories WHERE valid_to IS NULL
    ORDER BY VECTOR_DISTANCE(embedding, VECTOR_EMBEDDING({MODEL} USING :q AS data), COSINE)
    FETCH APPROX FIRST 1 ROWS ONLY),
hops AS (
    SELECT g.seed_id, g.related_id, LISTAGG(DISTINCT g.via, ', ') AS via
    FROM GRAPH_TABLE (memory_graph
           MATCH (m1 IS memory) -[IS mentions]-> (e IS entity) <-[IS mentions]- (m2 IS memory)
           WHERE m1.memory_id <> m2.memory_id
           COLUMNS (m1.memory_id AS seed_id, e.name AS via, m2.memory_id AS related_id)) g
    JOIN seed ON seed.memory_id = g.seed_id
    GROUP BY g.seed_id, g.related_id)
SELECT h.seed_id, h.related_id AS memory_id, m.user_id, h.via, m.content
FROM hops h JOIN memories m ON m.memory_id = h.related_id AND m.valid_to IS NULL
ORDER BY h.related_id FETCH FIRST 8 ROWS ONLY"""


def s8_without(p):
    question = p.get("question") or Q8
    sql, rows = vector_recall(question, k=1)
    return result(
        "The vector seed and nothing else: one memory, the budget figure",
        "bad",
        context=context(rows, "score"),
        question=question,
        sql=sql,
    )


def s8_with(p):
    question = p.get("question") or Q8
    _, seed = vector_recall(question, k=1)
    related = q(GRAPH_SQL, {"q": question})
    via = sorted({r["via"] for r in related})
    proved(
        "s8",
        f"seed {seed[0]['memory_id']} expanded through {', '.join(via)} to {len(related)} memories",
    )
    return result(
        f"Seed {seed[0]['memory_id']} plus {len(related)} memories that share an entity with it, in one statement",
        "good",
        context=context(seed, "score") + context(related, "via"),
        question=question,
        sql=GRAPH_SQL,
    )


# ----------------------------------------------------------------------------------------------- §9 ACID
Q9 = "Which database is the agent memory store for Cairn?"
FIX = "Decision: the team wants Oracle AI Database 26ai as the agent memory database for Cairn."
CORRECTION_SQL = """INSERT INTO memories (...) VALUES ('mem_007_v2', ..., VECTOR_EMBEDDING(... USING :content AS data));
UPDATE memories SET valid_to = :t WHERE memory_id = 'mem_007' AND valid_to IS NULL;
INSERT INTO memory_relations VALUES ('mem_007_v2', 'mem_007', 'supersedes');
COMMIT;"""


def restore_mem007():
    """Put the store back to before the correction, so either run can be repeated."""
    for stmt in (
        "DELETE FROM memory_artifacts WHERE memory_id = 'mem_007_v2'",
        "DELETE FROM memory_relations WHERE 'mem_007_v2' IN (src_id, dst_id)",
        "DELETE FROM memories WHERE memory_id = 'mem_007_v2'",
        "UPDATE memories SET valid_to = NULL WHERE memory_id = 'mem_007'",
    ):
        x(stmt)
    owner().commit()


def fix_binds():
    return memory_binds(
        "mem_007_v2",
        "global",
        "agent_planner",
        "semantic",
        0.95,
        datetime.now(UTC),
        "cairn",
        "doc",
        FIX,
    )


def s9_without(p):
    restore_mem007()
    binds, log = fix_binds(), []
    fix_vec, qv = (
        embed(FIX),
        embed(Q9),
    )  # embedded by the owner session; the other session only binds
    with session() as nocommit:
        nocommit.autocommit = True
        try:
            with nocommit.cursor() as cur:
                cur.setinputsizes(metadata=oracledb.DB_TYPE_JSON)
                cur.execute(
                    INSERT_MEMORY.replace(
                        f"VECTOR_EMBEDDING({MODEL} USING :content AS data)", ":embedding"
                    ),
                    binds | {"embedding": fix_vec},
                )
                log.append("write 1, INSERT mem_007_v2: committed on its own")
                cur.execute(
                    "UPDATE memories SET valid_to = :t WHERE memory_id = 'mem_007' AND valid_to = 'never'",
                    {"t": binds["created_at"]},
                )
        except oracledb.DatabaseError as e:
            log.append(f"write 2, close mem_007: failed with {first_line(e)}")
            log.append("write 3, the supersedes link: never ran")
        rows = q(BOUND_VECTOR_SQL.format(k=3), {"qv": qv}, conn=nocommit)
    return result(
        "The new fact landed, the old one stayed open: the agent now recalls two contradictory decisions",
        "bad",
        context=context(rows),
        question=Q9,
        user="Ada",
        log=log,
        note="Autocommit stands in for a store with no multi-record transaction.",
    )


def s9_with(p):
    restore_mem007()
    binds, log, conn = fix_binds(), [], owner()
    STATE["scn_before"] = int(
        q("SELECT DBMS_FLASHBACK.GET_SYSTEM_CHANGE_NUMBER AS scn FROM dual")[0]["scn"]
    )
    with conn.cursor() as cur:
        cur.setinputsizes(metadata=oracledb.DB_TYPE_JSON)
        cur.execute(INSERT_MEMORY, binds)
        cur.execute(
            "UPDATE memories SET valid_to = :t WHERE memory_id = 'mem_007' AND valid_to IS NULL",
            {"t": binds["created_at"]},
        )
        cur.execute("INSERT INTO memory_relations VALUES ('mem_007_v2', 'mem_007', 'supersedes')")
    conn.commit()
    with session() as other:
        seen = q(
            "SELECT memory_id, valid_to FROM memories WHERE memory_id LIKE 'mem_007%' ORDER BY 1",
            conn=other,
        )
    log.append(
        "a second session sees: "
        + "; ".join(f"{r['memory_id']} valid_to={r['valid_to'] or 'open'}" for r in seen)
    )
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE memories SET importance = 0.99 WHERE memory_id = 'mem_007_v2'")
            cur.execute(
                """INSERT INTO memories (memory_id, user_id, agent_id, memory_type, content)
                           VALUES ('mem_bad', 'user_ada', 'agent_planner', 'hunch', 'this type is not allowed')"""
            )
        conn.commit()
    except oracledb.DatabaseError as e:
        conn.rollback()
        log.append(f"a deliberate CHECK violation: {first_line(e)} → the whole unit rolled back")
    _, rows = vector_recall(Q9, k=3)
    proved(
        "s9", "three writes committed as one unit; a constraint violation rolled the next unit back"
    )
    return result(
        "Insert, close and link committed as one unit: the agent recalls one current decision",
        "good",
        context=context(rows, "score"),
        question=Q9,
        user="Ada",
        log=log,
        sql=CORRECTION_SQL,
    )


# ----------------------------------------------------------------------------------------------- §10 forget, don't delete
def s10_without(p):
    rows = q(
        "SELECT memory_id, valid_to, content FROM memories WHERE memory_id LIKE 'mem_007%' ORDER BY 1"
    )
    return result(
        "A store with no history can only tell you what the row says now",
        "bad",
        rows=rows,
        note="What did the agent believe before the correction? Without history, nobody can say.",
    )


def s10_with(p):
    log = []
    if STATE.get("scn_before") is None:
        s9_with({})
        log.append("ran §9's correction first, so there is a 'before' to read")
    scn = STATE["scn_before"]
    clocks = q(
        """SELECT :scn AS scn_before, SCN_TO_TIMESTAMP(:scn) AS scn_before_time,
                         DBMS_FLASHBACK.GET_SYSTEM_CHANGE_NUMBER AS scn_now, SYSTIMESTAMP AS time_now FROM dual""",
        {"scn": scn},
    )[0]
    then = q(
        "SELECT memory_id, valid_to, content FROM memories AS OF SCN :scn WHERE memory_id LIKE 'mem_007%' ORDER BY 1",
        {"scn": scn},
    )
    versions = q(
        """SELECT versions_operation AS op, versions_starttime AS started, memory_id, valid_to
                    FROM memories VERSIONS BETWEEN SCN :scn AND MAXVALUE
                    WHERE memory_id = 'mem_007' ORDER BY versions_starttime NULLS FIRST""",
        {"scn": scn},
    )
    log.append(
        "row history of mem_007: "
        + "; ".join(f"{v['op'] or '(before)'} at {v['started'] or '-'}" for v in versions)
    )
    proved("s10", "AS OF SCN read the pre-correction store; VERSIONS BETWEEN listed the change")
    return result(
        f"AS OF SCN {scn}: the table as it was just before the correction, rebuilt from undo",
        "good",
        rows=then,
        log=log,
        metrics=[[k, str(v)] for k, v in clocks.items()],
        sql="SELECT memory_id, valid_to, content FROM memories AS OF SCN :scn WHERE memory_id LIKE 'mem_007%'",
    )


# ----------------------------------------------------------------------------------------------- §11 duality
DOC = {
    "_id": "mem_doc_001",
    "userId": "user_cy",
    "agentId": "agent_coder",
    "type": "semantic",
    "importance": 0.5,
    "content": "Cy wrote this memory as a JSON document.",
    "metadata": {"project": "comet", "channel": "chat"},
}


def s11_without(p):
    doc_store, row_store = {"importance": 0.5}, {"importance": 0.5}
    doc_store["importance"] = 0.8  # agent A updates the document store; the sync job has not run
    log = [
        "agent A writes 0.8 to the document store",
        f"agent B reads the relational store: {row_store['importance']}",
    ]
    row_store["importance"] = 0.1  # agent B writes without knowing A did
    log += [
        "agent B writes 0.1 to the relational store",
        "the sync job copies documents over rows: B's write is lost",
    ]
    return result(
        "Two stores, a sync job, and a lost update nobody was told about",
        "bad",
        rows=[
            {"store": "document store", "importance": doc_store["importance"]},
            {"store": "relational store", "importance": row_store["importance"]},
        ],
        log=log,
        note="Simulated: two dicts stand in for a document database and a relational one.",
    )


def s11_with(p):
    if not q("SELECT 1 FROM memories WHERE memory_id = 'mem_doc_001'"):
        with owner().cursor() as cur:
            cur.setinputsizes(oracledb.DB_TYPE_JSON)
            cur.execute("INSERT INTO memory_dv (data) VALUES (:1)", [DOC])
        owner().commit()
    read = "SELECT JSON_SERIALIZE(data) AS d FROM memory_dv WHERE JSON_VALUE(data, '$._id') = 'mem_doc_001'"
    write = "UPDATE memory_dv SET data = :1 WHERE JSON_VALUE(data, '$._id') = 'mem_doc_001'"
    log = []
    with session() as a, session() as b:
        doc_a, doc_b = (json.loads(q(read, conn=c)[0]["d"]) for c in (a, b))
        log.append(
            f"agents A and B read the same document, etag {doc_a['_metadata']['etag'][:12]}…"
        )
        with a.cursor() as cur:
            cur.setinputsizes(oracledb.DB_TYPE_JSON)
            cur.execute(write, [{**doc_a, "importance": 0.8}])
        a.commit()
        log.append("agent A writes importance 0.8 with its etag: accepted")
        try:
            with b.cursor() as cur:
                cur.setinputsizes(oracledb.DB_TYPE_JSON)
                cur.execute(write, [{**doc_b, "importance": 0.1}])
            b.commit()
            log.append("agent B's stale write went through")
        except oracledb.DatabaseError as e:
            b.rollback()
            log.append(f"agent B writes with the stale etag: refused, {first_line(e)}")
    row = q(
        "SELECT memory_id, user_id, memory_type, importance, content FROM memories WHERE memory_id = 'mem_doc_001'"
    )
    proved("s11", "one copy as rows and documents; a stale etag was refused")
    return result(
        "One copy, two shapes: the document write landed as a row, and the stale etag was refused",
        "good",
        rows=row,
        log=log,
        extra={"document": json.loads(q(read)[0]["d"])},
        sql=write,
    )


# ----------------------------------------------------------------------------------------------- §12 files and the scratchpad
def s12_without(p):
    memory = {"memory_id": "mem_051", "report_url": "s3://agent-artifacts/cairn/weekly_report.md"}
    bucket = {"cairn/weekly_report.md": "# Weekly memory report ..."}
    log = [
        f"memory row points at {memory['report_url']}",
        "the memory is deleted on a user's request",
        f"the object store still holds {list(bucket)}: no policy, audit or delete reached it",
        "the agent's scratch working sat in /tmp on the agent host and was lost on restart",
    ]
    return result(
        "The file outlived the memory: a URL is a pointer the database's rules never see",
        "bad",
        log=log,
        rows=[
            {"where": "memory store", "has mem_051": "no"},
            {"where": "object store", "has mem_051": "yes, orphaned"},
        ],
        note="Simulated: a dict stands in for an object store.",
    )


def s12_with(p):
    arts = q(
        """SELECT artifact_id, memory_id, mime_type, file_name, DBMS_LOB.GETLENGTH(text_body) AS text_bytes,
                       DBMS_LOB.GETLENGTH(binary_body) AS binary_bytes FROM memory_artifacts ORDER BY artifact_id"""
    )
    png = q(
        "SELECT binary_body FROM memory_artifacts WHERE mime_type = 'image/png' FETCH FIRST 1 ROWS ONLY"
    )
    note = q(
        "SELECT text_body FROM memory_artifacts WHERE mime_type = 'text/markdown' AND memory_id = 'mem_051'"
    )
    log, conn = [], owner()
    x("DELETE FROM memories WHERE memory_id = 'mem_051'")
    log.append(
        "DELETE mem_051 inside a transaction: its artifacts left now = "
        f"{q('SELECT COUNT(*) AS n FROM memory_artifacts WHERE memory_id = :m', {'m': 'mem_051'})[0]['n']} (ON DELETE CASCADE)"
    )
    conn.rollback()
    log.append("ROLLBACK: the memory and both files are back, together")
    proved(
        "s12", "CLOB and BLOB artifacts with a foreign key; deleting the memory deletes its files"
    )
    return result(
        "Files are rows next to their memory: same transaction, same delete, same policy",
        "good",
        rows=arts,
        log=log,
        extra={
            "image": "data:image/png;base64," + base64.b64encode(png[0]["binary_body"]).decode()
            if png
            else None,
            "files": [
                {
                    "path": "memory_artifacts/weekly_report.md",
                    "content": note[0]["text_body"] if note else "",
                }
            ],
        },
    )


SCRATCH = "/scratch/agent/"
OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
}


def fs_read(path):
    rows = q("SELECT filedata FROM dbfs_content WHERE pathname = :p", {"p": path})
    return rows[0]["filedata"].decode() if rows else None


def fs_write(path, text):
    if fs_read(path) is not None:
        x("BEGIN DBMS_DBFS_CONTENT.deleteFile(:p); END;", {"p": path})
    body = owner().createlob(oracledb.DB_TYPE_BLOB)
    body.write(text.encode())
    x(
        """DECLARE props DBMS_DBFS_CONTENT_PROPERTIES_T := DBMS_DBFS_CONTENT_PROPERTIES_T(); body BLOB := :body;
         BEGIN DBMS_DBFS_CONTENT.createFile(:path, props, body); END;""",
        {"path": path, "body": body},
    )
    owner().commit()


def fs_list():
    return q(
        """SELECT pathname, DBMS_LOB.GETLENGTH(filedata) AS bytes, std_modification_time AS modified
                FROM dbfs_content WHERE pathname LIKE :p AND pathtype = 'file' ORDER BY pathname""",
        {"p": SCRATCH + "%"},
    )


def arithmetic(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, int | float):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in OPS:
        return OPS[type(node.op)](arithmetic(node.left), arithmetic(node.right))
    raise ValueError("only numbers and + - * / are allowed")


def promote(content, working):
    """One transaction: a new long-term memory, embedded in the INSERT, plus its working as an artifact."""
    memory_id, conn = f"mem_promoted_{uuid.uuid4().hex[:5]}", owner()
    try:
        with conn.cursor() as cur:
            cur.setinputsizes(metadata=oracledb.DB_TYPE_JSON)
            cur.execute(
                INSERT_MEMORY,
                memory_binds(
                    memory_id,
                    "global",
                    "agent_claude",
                    "semantic",
                    0.8,
                    datetime.now(UTC),
                    "cairn",
                    "scratchpad",
                    content,
                ),
            )
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO memory_artifacts VALUES (:1, :2, 'text/markdown', :3, :4, NULL)",
                [f"art_{memory_id[4:]}", memory_id, "worksheet.md", working],
            )
        conn.commit()
    except oracledb.DatabaseError:
        conn.rollback()
        raise
    return memory_id


SCRATCH_TASK = (
    "How far over its Q3 cloud budget was Cairn in August? Find the monthly overspend in dollars and the total "
    "for the quarter if it continued. Recall the facts you need, compute every figure with calculate (each line "
    "is recorded in a worksheet in your scratchpad), read the worksheet back, then promote the final figures to "
    "long-term memory."
)


def s12_scratchpad(p):
    if not claude.client:
        return result(
            "Skipped: set ANTHROPIC_API_KEY to let Claude use the scratchpad.", status="skipped"
        )
    for row in fs_list():
        x("BEGIN DBMS_DBFS_CONTENT.deleteFile(:p); END;", {"p": row["pathname"]})
    owner().commit()
    trace, promoted = [], []
    from anthropic import beta_tool

    @beta_tool
    def recall_facts(query: str) -> str:
        """Search long-term memory and return the five closest memories."""
        _, rows = vector_recall(query, k=5)
        trace.append(f"recall_facts({query!r}) → {', '.join(r['memory_id'] for r in rows)}")
        return json.dumps([{"memory_id": r["memory_id"], "content": r["content"]} for r in rows])

    @beta_tool
    def calculate(filename: str, label: str, expression: str) -> str:
        """Evaluate an arithmetic expression and append `label: expression = result` to a worksheet in your scratchpad.

        Args:
            filename: A plain worksheet file name, such as budget.md. Created on first use.
            label: What the line computes, for example "monthly overspend".
            expression: Numbers and + - * / only, for example 42000 * 0.38.
        """
        if not re.fullmatch(r"[\w.-]{1,60}", filename):
            return "error: use a plain file name such as budget.md"
        try:
            value = round(arithmetic(ast.parse(expression, mode="eval").body), 2)
        except (SyntaxError, ValueError, ZeroDivisionError) as e:
            return f"error: {e}"
        path = SCRATCH + filename
        fs_write(
            path, (fs_read(path) or f"# {filename}\n\n") + f"- {label}: {expression} = {value:,}\n"
        )
        trace.append(f"calculate({label!r}: {expression} = {value:,}) → {path}")
        return f"{value} (appended to {path})"

    @beta_tool
    def scratch_read(filename: str) -> str:
        """Read a file back from your scratchpad."""
        trace.append(f"scratch_read({SCRATCH + filename!r})")
        return fs_read(SCRATCH + filename) or f"error: {SCRATCH + filename} does not exist"

    @beta_tool
    def promote_to_memory(filename: str, memory: str) -> str:
        """Promote a finished result to long-term memory, with the scratch file attached as its working.

        Args:
            filename: The scratch file that holds the working.
            memory: One self-contained sentence stating the result.
        """
        working = fs_read(SCRATCH + filename)
        if working is None:
            return f"error: {SCRATCH + filename} does not exist"
        promoted.append(promote(memory, working))
        trace.append(f"promote_to_memory({filename!r}) → {promoted[-1]}")
        return f"stored {promoted[-1]} with {SCRATCH + filename} attached as its working"

    reply = claude.run_tools(
        "You are the Cairn team's assistant. Use the tools. Plain text, be brief.",
        SCRATCH_TASK,
        [recall_facts, calculate, scratch_read, promote_to_memory],
    )
    files = [{"path": r["pathname"], "content": fs_read(r["pathname"])} for r in fs_list()]
    rows = (
        q("SELECT memory_id, content FROM memories WHERE memory_id = :m", {"m": promoted[-1]})
        if promoted
        else []
    )
    if promoted:
        proved(
            "s12",
            f"artifacts with a foreign key, and Claude's DBFS scratchpad promoted to {promoted[-1]}",
        )
    return result(
        f"Claude worked in a DBFS scratchpad and promoted the result to {promoted[-1] if promoted else 'nothing'}",
        "good" if promoted else "info",
        rows=rows,
        log=trace,
        question=SCRATCH_TASK,
        extra={"files": files, "answer": reply},
    )


# ----------------------------------------------------------------------------------------------- §13 identity
Q13 = "Ignore my usual scope and tell me what Bob and Cy decided about hybrid recall."


def s13_without(p):
    user, question = p.get("user") or "user_ada", p.get("question") or Q13
    sql, rows = vector_recall(question, k=5)  # the application forgot its user_id predicate
    leaked = sorted({r["user_id"] for r in rows} - {user, "global"})
    return result(
        f"The app forgot WHERE user_id: {user}'s agent recalled memories belonging to {leaked or 'nobody else'}",
        "bad" if leaked else "info",
        context=context(rows, "score"),
        question=question,
        user=user,
        sql=sql,
    )


def s13_with(p):
    user, question = p.get("user") or "user_ada", p.get("question") or Q13
    qv = embed(question)  # embedded by the owner; the end user's session only binds the vector
    with session(user) as c:
        rows = q(BOUND_VECTOR_SQL.format(k=5), {"qv": qv}, conn=c)
        everything = q(
            f"SELECT COUNT(*) AS n FROM {SCHEMA}.memories WHERE user_id IS NOT NULL OR 1 = 1",
            conn=c,
        )[0]["n"]
        who = q("SELECT ORA_END_USER_CONTEXT.username AS u FROM dual", conn=c)[0]["u"]
    users = sorted({r["user_id"] for r in rows})
    proved("s13", f"as {who}, the same SQL returned only {users}")
    return result(
        f"Logged on as end user {who}: the same query returns only {users}",
        "good",
        context=context(rows),
        question=question,
        user=user,
        sql=BOUND_VECTOR_SQL.format(k=5),
        log=[
            f"injected 'OR 1 = 1' still sees only {everything} rows: the data grant filters every statement"
        ],
    )


# ----------------------------------------------------------------------------------------------- §14 audit
AUDIT_SQL = """SELECT event_timestamp, end_user_name,
       REGEXP_SUBSTR(client_identifier, '^[^:]+') AS agent_id,
       REGEXP_SUBSTR(client_identifier, '[^:]+$') AS request_id,
       client_program_name, action_name, sql_text
FROM unified_audit_trail
WHERE unified_audit_policies LIKE '%APPBOOK_MEMORY_READS%' AND client_identifier LIKE :run
ORDER BY event_timestamp"""
READS = [("user_ada", "agent_planner"), ("user_ada", "agent_coder"), ("user_bob", "agent_planner")]


def s14_without(p):
    app_log = [f"{who} via {agent}: recall_memories" for who, agent in READS[:2]]
    return result(
        "The application log has 2 of 3 reads: nobody added logging to the coder's debug path",
        "bad",
        rows=[
            {"read": f"{who} via {agent}", "in the app log": "yes" if i < 2 else "no"}
            for i, (who, agent) in enumerate(READS)
        ],
        log=app_log,
        note="Simulated: an application-side log only knows what the code remembered to write.",
    )


def s14_with(p):
    run = uuid.uuid4().hex[:6]
    for who, agent in READS:
        with session(who) as c:
            c.client_identifier = f"{agent}:req-{run}-{who[5:]}"
            q(f"SELECT COUNT(*) AS n FROM {SCHEMA}.memories", conn=c)
    x("BEGIN DBMS_AUDIT_MGMT.FLUSH_UNIFIED_AUDIT_TRAIL; END;", ignore=True)
    trail = q(AUDIT_SQL, {"run": f"%:req-{run}-%"})
    per = {}
    for r in trail:
        per[(r["end_user_name"], r["agent_id"])] = (
            per.get((r["end_user_name"], r["agent_id"]), 0) + 1
        )
    proved("s14", f"{len(trail)} audit rows with the end user, the agent and the request")
    return result(
        f"Unified Auditing recorded all {len(trail)} reads: the person, the agent and the request on every row",
        "good",
        rows=trail,
        sql=AUDIT_SQL,
        log=[f"{u} via {a}: {n} read(s)" for (u, a), n in sorted(per.items())],
    )


# ----------------------------------------------------------------------------------------------- §15 the agent
def recall_for(end_user_conn, query, k):
    """Embed in the owner session, select candidates in the end user's session, rerank in the owner session."""
    qv = embed(query)
    sync_text()
    ids = TICKET.findall(query)
    exact = f"UNION SELECT memory_id FROM {SCHEMA}.memories WHERE valid_to IS NULL AND CONTAINS(content, :ids) > 0"
    cands = q(
        f"""SELECT memory_id FROM (SELECT memory_id FROM {SCHEMA}.memories WHERE valid_to IS NULL
                  ORDER BY VECTOR_DISTANCE(embedding, :qv, COSINE) FETCH APPROX FIRST 20 ROWS ONLY) {exact if ids else ''}""",
        {"qv": qv} | ({"ids": " OR ".join("{%s}" % i for i in ids)} if ids else {}),
        conn=end_user_conn,
    )
    score, binds = (
        (f"PREDICTION({RERANKER} USING (:q || ' ¶ ' || content) AS DATA)", {"q": query})
        if STATE.get("reranker")
        else ("-VECTOR_DISTANCE(embedding, :qv, COSINE)", {"qv": qv})
    )
    return q(
        f"""SELECT memory_id, user_id, TO_CHAR(created_at, 'YYYY-MM-DD') AS created, content, ROUND({score}, 2) AS relevance
                 FROM memories WHERE memory_id IN (SELECT id FROM JSON_TABLE(:ids, '$[*]' COLUMNS (id VARCHAR2(40) PATH '$')))
                 ORDER BY relevance DESC FETCH FIRST :k ROWS ONLY""",
        binds | {"ids": json.dumps([c["memory_id"] for c in cands]), "k": k},
    )


def s15_without(p):
    if not claude.client:
        return result("Skipped: set ANTHROPIC_API_KEY.", status="skipped")
    message = p.get("message") or "When does the deploy freeze for memory services start?"
    reply = claude.answer_without_memory(message)
    return result(
        "Claude with no memory: every session starts from nothing",
        "bad",
        question=message,
        extra={"answer": reply},
        note="The same model, no tools, no recall.",
    )


def s15_with(p):
    if not claude.client:
        return result("Skipped: set ANTHROPIC_API_KEY.", status="skipped")
    user = p.get("user") or "user_ada"
    message = p.get("message") or "When does the deploy freeze for memory services start?"
    request_id = f"agent-{uuid.uuid4().hex[:8]}"
    trace, written = [], []
    from anthropic import beta_tool

    with session(user) as c:
        c.client_identifier = f"agent_claude:{request_id}"
        who = q("SELECT ORA_END_USER_CONTEXT.username AS u FROM dual", conn=c)[0]["u"]

        @beta_tool
        def recall_memories(query: str, k: int) -> str:
            """Search this user's long-term memory (their own plus team-wide memories). Use it before answering anything
            about past decisions, incidents, preferences or procedures.

            Args:
                query: What to look for, in natural language. Include exact ticket IDs if known.
                k: How many memories to return, 1 to 8.
            """
            rows = recall_for(c, query, max(1, min(k, 8)))
            found = ", ".join(f"{r['memory_id']} ({r['relevance']})" for r in rows)
            trace.append(f"recall_memories({query!r}) → {found}")
            return json.dumps(
                [{k_: r[k_] for k_ in ("memory_id", "user_id", "created", "content")} for r in rows]
            )

        @beta_tool
        def remember(
            content: str,
            memory_type: Literal["semantic", "episodic", "procedural"],
            project: Literal["cairn", "beacon", "comet"],
        ) -> str:
            """Store a new durable memory for this user. Not for changing an existing memory: use correct_memory for that.

            Args:
                content: One self-contained sentence.
                memory_type: semantic (a fact or decision), episodic (an event) or procedural (how to do something).
                project: The project the memory belongs to.
            """
            memory_id = f"mem_{uuid.uuid4().hex[:8]}"
            with owner().cursor() as cur:
                cur.setinputsizes(metadata=oracledb.DB_TYPE_JSON)
                cur.execute(
                    INSERT_MEMORY,
                    memory_binds(
                        memory_id,
                        who,
                        "agent_claude",
                        memory_type,
                        0.8,
                        datetime.now(UTC),
                        project,
                        "agent",
                        content,
                        request_id,
                    ),
                )
            owner().commit()
            written.append(memory_id)
            trace.append(f"remember({content[:70]!r}) → {memory_id}")
            return json.dumps({"stored": memory_id})

        @beta_tool
        def correct_memory(memory_id: str, corrected_content: str) -> str:
            """Replace a memory that is now wrong: writes the corrected memory, closes the old one and links them, in one
            transaction. Use the memory_id returned by recall_memories.

            Args:
                memory_id: The memory that is out of date.
                corrected_content: The full corrected memory, one self-contained sentence.
            """
            old = q(
                f"SELECT user_id, memory_type, metadata FROM {SCHEMA}.memories WHERE memory_id = :id AND valid_to IS NULL",
                {"id": memory_id},
                conn=c,
            )
            if not old:
                return json.dumps(
                    {"error": f"{memory_id} is not a current memory this user can see"}
                )
            new_id, conn = f"{memory_id}_c{uuid.uuid4().hex[:4]}", owner()
            try:
                with conn.cursor() as cur:
                    cur.setinputsizes(metadata=oracledb.DB_TYPE_JSON)
                    cur.execute(
                        INSERT_MEMORY,
                        memory_binds(
                            new_id,
                            old[0]["user_id"],
                            "agent_claude",
                            old[0]["memory_type"],
                            0.9,
                            datetime.now(UTC),
                            old[0]["metadata"]["project"],
                            "agent",
                            corrected_content,
                            request_id,
                        ),
                    )
                    cur.execute(
                        "UPDATE memories SET valid_to = SYSTIMESTAMP WHERE memory_id = :id AND valid_to IS NULL",
                        {"id": memory_id},
                    )
                    cur.execute(
                        "INSERT INTO memory_relations VALUES (:n, :o, 'supersedes')",
                        {"n": new_id, "o": memory_id},
                    )
                conn.commit()
            except oracledb.DatabaseError:
                conn.rollback()
                raise
            written.append(new_id)
            trace.append(f"correct_memory({memory_id}) → {new_id} supersedes {memory_id}")
            return json.dumps({"stored": new_id, "supersedes": memory_id})

        reply = claude.run_tools(
            claude.AGENT_SYSTEM,
            message,
            [recall_memories, remember, correct_memory],
            effort="medium",
        )
    proved("s15", f"Claude used Oracle memory tools as {who}; wrote {written or 'nothing'}")
    return result(
        f"Claude with three Oracle memory tools, running as end user {who}",
        "good",
        question=message,
        user=user,
        log=trace,
        extra={"answer": reply, "written": written, "request_id": request_id},
    )


RUNS = {
    "s1": {"without": s1_without, "with": s1_with},
    "s2": {"without": s2_without, "with": s2_with},
    "s3": {"without": s3_without, "with": s3_with},
    "s4": {"without": s4_without, "with": s4_with},
    "s5": {"without": s5_without, "with": s5_with},
    "s6": {"without": s6_without, "with": s6_with},
    "s7": {"without": s7_without, "with": s7_with},
    "s8": {"without": s8_without, "with": s8_with},
    "s9": {"without": s9_without, "with": s9_with},
    "s10": {"without": s10_without, "with": s10_with},
    "s11": {"without": s11_without, "with": s11_with},
    "s12": {"without": s12_without, "with": s12_with, "scratchpad": s12_scratchpad},
    "s13": {"without": s13_without, "with": s13_with},
    "s14": {"without": s14_without, "with": s14_with},
    "s15": {"without": s15_without, "with": s15_with},
}


def run(sid, action, params):
    with LOCK:
        return RUNS[sid][action](params or {})
