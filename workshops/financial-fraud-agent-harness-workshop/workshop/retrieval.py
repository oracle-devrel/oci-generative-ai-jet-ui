"""Plumbing for Part 3 (retrieval): the AML knowledge store, reranker, result shaping."""
import hashlib
import json
import re

import oracledb
from langchain_oracledb.vectorstores.oraclevs import INTERNAL_ID_KEY

from workshop.aml_knowledge import AML_NOTES
from workshop.memory import find_memory

KNOWLEDGE_TABLE = "AML_KNOWLEDGE_VS"
RERANKER_MODEL = "RERANKER_ONNX"

_RERANK_SQL = f"""
    SELECT t.idx, PREDICTION({RERANKER_MODEL} USING :q AS DATA1, t.content AS DATA2)
      FROM JSON_TABLE(:docs, '$[*]' COLUMNS (
             idx NUMBER PATH '$.index', content VARCHAR2(4000) PATH '$.content')) t
     ORDER BY 2 DESC FETCH FIRST :k ROWS ONLY"""


def _json_safe(meta):
    """OAMP metadata can hold Decimals and datetimes; keep only what json can serialise."""
    return json.loads(json.dumps(meta or {}, default=str))


def make_reranker(conn):
    """Return rerank(query, candidates, top_k, content_key): the in-DB cross-encoder.

    Falls back to the incoming order when no RERANKER_ONNX model is registered.
    """
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM user_mining_models WHERE model_name = :m", m=RERANKER_MODEL)
        loaded = cur.fetchone()[0] > 0

    def rerank(query, candidates, top_k=5, content_key="body"):
        if not candidates or not loaded:
            return candidates[:top_k]
        docs = [{"index": i, "content": str(c.get(content_key, ""))[:1500]}
                for i, c in enumerate(candidates)]
        try:
            with conn.cursor() as cur:
                cur.execute(_RERANK_SQL, q=query, docs=json.dumps(docs), k=top_k)
                ranked = list(cur)
        except oracledb.DatabaseError:
            return candidates[:top_k]
        out = []
        for idx, score in ranked:
            if idx is not None and int(idx) < len(candidates):
                out.append({**candidates[int(idx)], "rerank_score": float(score or 0.0)})
        return out

    return rerank


def to_hit(doc, **extra):
    """LangChain Document from knowledge_vs -> the dict the agent tools return."""
    meta = _json_safe(doc.metadata)
    return {"kind": meta.get("kind") or "memory", "subject": meta.get("subject", ""),
            "body": doc.page_content, "metadata": meta, **extra}


def _oamp_rows(client, user_id, agent_id):
    """Current, valid OAMP memories written as Facts (kind and subject set), latest per pair, no tool output."""
    latest = {}
    for r in client._store.list("memory", user_id=user_id, agent_id=agent_id, limit=None):
        meta = r.metadata or {}
        if str(getattr(r.status, "value", r.status)).lower() != "valid" or not r.content:
            continue
        if not meta.get("kind") or not meta.get("subject") or meta["kind"] == "tool_output":
            continue
        latest[(meta["kind"], meta["subject"])] = r
    return list(latest.values())


_STOPWORDS = {"the", "and", "for", "what", "which", "how", "does", "with", "that", "this", "are",
              "was", "were", "you", "your", "from", "into", "its", "their", "than", "then", "can"}


def keyword_terms(query):
    """Query text for the Oracle Text leg: identifiers split at '_' (the index tokenises that way),
    stop words dropped. 'which column is RATE_BP?' -> 'column rate bp'."""
    terms = [t for t in re.findall(r"[a-z0-9]+", (query or "").lower()) if len(t) > 1 and t not in _STOPWORDS]
    return " ".join(dict.fromkeys(terms)) or (query or "")


def _knowledge_row(record_id, body, meta):
    meta = _json_safe(meta)
    meta["kind"] = meta.get("kind") or "memory"
    body = body[:1500]
    meta["knowledge_hash"] = hashlib.sha256(body.encode()).hexdigest()[:16]
    return record_id, body, meta


TEXT_INDEX = "AML_KNOWLEDGE_TEXT_IDX"


def refresh_text_index(conn):
    """Oracle Text indexes catch up asynchronously; sync so new rows are searchable now."""
    with conn.cursor() as cur:
        try:
            cur.callproc("ctx_ddl.sync_index", [TEXT_INDEX])
        except oracledb.DatabaseError:
            pass   # index not created yet


def sync_knowledge(vs, client, user_id, agent_id):
    """Make AML_KNOWLEDGE_VS mirror the AML notes plus the valid OAMP memories.

    OAMP is the source of truth: each row uses the OAMP record id, rows are upserted, and rows whose
    record is gone (retired, replaced, tool output) are deleted. Returns (notes, memories).
    """
    rows = [_knowledge_row(f"aml-note-{i:02d}", body, {"kind": "policy", "subject": subject, "origin": "aml_notes"})
            for i, (subject, body) in enumerate(AML_NOTES, 1)]
    rows += [_knowledge_row(r.id, r.content, r.metadata) for r in _oamp_rows(client, user_id, agent_id)]
    with vs.client.cursor() as cur:
        cur.execute(f"SELECT JSON_VALUE(metadata, '$.{INTERNAL_ID_KEY}'), JSON_VALUE(metadata, '$.knowledge_hash') "
                    f"FROM {vs.table_name}")
        have = dict(cur.fetchall())
    stale = [i for i in have if i not in {r[0] for r in rows}]
    if stale:
        vs.delete(ids=stale)
        refresh_text_index(vs.client)
    todo = [r for r in rows if have.get(r[0]) != r[2]["knowledge_hash"]]   # new or changed only
    if todo:
        ids, texts, metas = zip(*todo)
        vs.add_texts(list(texts), list(metas), ids=list(ids))
        refresh_text_index(vs.client)
    return len(AML_NOTES), len(rows) - len(AML_NOTES)


def mirror_writes(write_facts, vs, client, user_id, agent_id):
    """Wrap write_facts so every fact it stores is also upserted into knowledge_vs."""
    def write_and_index(facts, *args, **kwargs):
        counts = write_facts(facts, *args, **kwargs)
        for f in facts:
            rec = find_memory(client, user_id, agent_id, f.kind, f.subject)
            if rec is None or f.kind == "tool_output":
                continue
            with vs.client.cursor() as cur:   # replace any older row for the same kind and subject
                cur.execute(f"DELETE FROM {vs.table_name} WHERE JSON_VALUE(metadata, '$.kind') = :k "
                            "AND JSON_VALUE(metadata, '$.subject') = :s", k=f.kind, s=f.subject)
            vs.client.commit()
            _, body, meta = _knowledge_row(rec.id, rec.content, rec.metadata)
            vs.add_texts([body], [meta], ids=[rec.id])
        refresh_text_index(vs.client)
        return counts
    return write_and_index


def prepare_search(conn, vs, scanner, client, user_id, agent_id):
    """Set up search over knowledge_vs: HNSW + Oracle Text indexes, the in-DB reranker, and mirrored writes.

    After this, scanner.write_facts (and so run_scan) also updates knowledge_vs. Returns (rerank, write_facts).
    """
    from langchain_oracledb.retrievers.text_search import create_text_index
    from langchain_oracledb.vectorstores.oraclevs import create_index

    create_index(conn, vs, params={"idx_name": "AML_KNOWLEDGE_HNSW", "idx_type": "HNSW"})
    create_text_index(conn, TEXT_INDEX, vector_store=vs)   # keyword search, used by 3.3
    scanner.write_facts = mirror_writes(scanner.write_facts, vs, client, user_id, agent_id)
    return make_reranker(conn), scanner.write_facts


def check_retrieve_knowledge(retrieve_knowledge):
    """Checkpoint for TODO 4."""
    _q = "how are transaction amounts stored"
    _hits = retrieve_knowledge(_q, k=3, kinds="column")
    assert _hits, "❌ TODO 4: retrieve_knowledge returned no hits."
    assert {"kind", "subject", "body", "metadata", "distance"} <= _hits[0].keys(), "❌ TODO 4: each hit needs kind, subject, body, metadata, distance."
    assert all(h["kind"] == "column" for h in _hits), "❌ TODO 4: the kinds filter was not applied (pass filter=flt to the search)."
    assert len(_hits) <= 3, "❌ TODO 4: return at most k hits."
    _two = retrieve_knowledge(_q, k=6, kinds="column,policy")
    assert _two and {h["kind"] for h in _two} <= {"column", "policy"}, "❌ TODO 4: 'a,b' must split into two kinds."
    _pol = retrieve_knowledge("structuring cash deposits below the reporting threshold", k=3, kinds=["policy"])
    assert _pol and all(h["kind"] == "policy" for h in _pol), "❌ TODO 4: kinds may also be a list."
    assert len(retrieve_knowledge(_q, k=3)) == 3, "❌ TODO 4: without kinds (flt = None), return k hits from every kind."
    assert len(retrieve_knowledge(_q, k=1)) == 1, "❌ TODO 4: k=1 must return exactly one hit."
    print("✅ TODO 4 passed: retrieve_knowledge filters by kind and returns at most k hits.")
