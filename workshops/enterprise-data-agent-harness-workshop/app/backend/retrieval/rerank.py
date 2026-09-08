"""Cross-encoder rerank helper.

Mirrors the notebook §3.5 `rerank()` function — given a list of candidate
records (each a dict with at least a `content_key`-named field) and a query,
issue a single SQL call that runs PREDICTION(reranker USING :q AS DATA1,
content AS DATA2) over every candidate, returning the top-k by score.

Falls through to cosine-input order when no reranker is registered, so the
agent's retrieval code is identical whether or not the reranker is loaded.
"""

from __future__ import annotations

import json

import oracledb


def rerank_factory(agent_conn, model_name: str | None):
    """Return a `rerank(query, candidates, top_k, content_key)` callable
    bound to the given connection + model.

    When `model_name` is None or the model isn't registered, the returned
    callable just slices the input list to top_k. That keeps callers
    indifferent to whether reranking is enabled.
    """

    def _model_loaded() -> bool:
        if not model_name:
            return False
        try:
            with agent_conn.cursor() as cur:
                cur.execute(
                    "SELECT COUNT(*) FROM user_mining_models WHERE model_name = :m",
                    m=model_name,
                )
                return cur.fetchone()[0] > 0
        except oracledb.DatabaseError:
            return False

    def rerank(query: str, candidates: list[dict],
               top_k: int = 5, content_key: str = "body") -> list[dict]:
        if not candidates:
            return candidates
        if not _model_loaded():
            return candidates[:top_k]

        # JSON_TABLE-style payload so we can rerank in one PL/SQL round-trip
        # rather than firing one PREDICTION per candidate from Python.
        docs = [
            {"index": i, "content": str(c.get(content_key, ""))[:1500]}
            for i, c in enumerate(candidates)
        ]
        sql = (
            f"SELECT t.idx, "
            f"       PREDICTION({model_name} USING :q AS DATA1, t.content AS DATA2) AS score "
            "  FROM JSON_TABLE(:docs, '$[*]' COLUMNS ("
            "         idx     NUMBER          PATH '$.index', "
            "         content VARCHAR2(4000)  PATH '$.content'"
            "       )) t "
            " ORDER BY score DESC "
            " FETCH FIRST :k ROWS ONLY"
        )
        try:
            with agent_conn.cursor() as cur:
                cur.execute(sql, q=query, docs=json.dumps(docs), k=top_k)
                ranked = list(cur)
        except oracledb.DatabaseError as e:
            print(f"[rerank] PREDICTION failed; falling back to cosine order: {e}")
            return candidates[:top_k]

        out: list[dict] = []
        for idx, score in ranked:
            if idx is None or int(idx) >= len(candidates):
                continue
            item = dict(candidates[int(idx)])
            try:
                item["rerank_score"] = float(score) if score is not None else 0.0
            except (TypeError, ValueError):
                item["rerank_score"] = 0.0
            out.append(item)
        return out

    rerank.model_loaded = _model_loaded
    rerank.model_name = model_name
    return rerank
