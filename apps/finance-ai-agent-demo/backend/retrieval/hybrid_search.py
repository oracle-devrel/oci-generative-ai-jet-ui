"""Hybrid search: vector + text (pre-filter, post-filter, RRF)."""

import array

from database.query_helper import execute_query
from retrieval.text_search import _sanitize_for_oracle_text


def _get_query_embedding(embedding_model, query):
    """Encode query to embedding array."""
    qv = embedding_model.embed_query(query)
    return array.array("f", qv)


def hybrid_pre_filter(conn, embedding_model, search_phrase, top_k=10, query_logger=None):
    """Pre-filter: keyword narrows first, then vector ranks."""
    qv = _get_query_embedding(embedding_model, search_phrase)
    safe_kw = _sanitize_for_oracle_text(search_phrase)

    # Subquery pattern: inner query uses raw columns for vector bind compat
    sql = f"""
        SELECT id, text, SUBSTR(text, 1, 200) AS text_snippet,
               ROUND(1 - distance, 4) AS similarity_score
        FROM (
            SELECT id, text, metadata,
                   vector_distance(embedding, :q, COSINE) as distance
            FROM KNOWLEDGE_BASE
            WHERE CONTAINS(text, :kw, 1) > 0
            ORDER BY distance
            FETCH APPROX FIRST {top_k} ROWS ONLY WITH TARGET ACCURACY 90
        )
        ORDER BY distance
    """

    return execute_query(
        conn,
        sql,
        {"q": qv, "kw": safe_kw},
        query_logger,
        description=f"Hybrid pre-filter (Vector + Text): '{search_phrase[:40]}'",
    )


def hybrid_post_filter(
    conn, embedding_model, search_phrase, top_k=10, candidate_k=200, query_logger=None
):
    """Post-filter: vector retrieves candidates, then keyword filters."""
    qv = _get_query_embedding(embedding_model, search_phrase)
    safe_kw = _sanitize_for_oracle_text(search_phrase)

    # Subquery pattern: inner query uses raw columns for vector bind compat
    sql = f"""
        WITH vec_candidates AS (
            SELECT id, text, metadata,
                   vector_distance(embedding, :q, COSINE) as distance
            FROM KNOWLEDGE_BASE
            ORDER BY distance
            FETCH APPROX FIRST {candidate_k} ROWS ONLY WITH TARGET ACCURACY 90
        )
        SELECT
            id,
            SUBSTR(text, 1, 200) AS text_snippet,
            ROUND(1 - distance, 4) AS similarity_score
        FROM vec_candidates
        WHERE CONTAINS(text, :kw, 1) > 0
        ORDER BY distance
        FETCH FIRST {top_k} ROWS ONLY
    """

    return execute_query(
        conn,
        sql,
        {"q": qv, "kw": safe_kw},
        query_logger,
        description=f"Hybrid post-filter (Vector + Text): '{search_phrase[:40]}'",
    )


def hybrid_rrf(
    conn, embedding_model, search_phrase, top_k=10, per_list=120, k=60, query_logger=None
):
    """Reciprocal Rank Fusion: fuse vector and text rankings."""
    qv = _get_query_embedding(embedding_model, search_phrase)
    safe_kw = _sanitize_for_oracle_text(search_phrase)

    # Subquery pattern: inner query uses raw columns for vector bind compat,
    # vec_ranked applies transformations on already-fetched rows.
    sql = f"""
        WITH
        vec_raw AS (
            SELECT id, text, metadata,
                   vector_distance(embedding, :q, COSINE) as distance
            FROM KNOWLEDGE_BASE
            ORDER BY distance
            FETCH APPROX FIRST {per_list} ROWS ONLY WITH TARGET ACCURACY 90
        ),
        vec AS (
            SELECT id,
                   SUBSTR(text, 1, 200) AS text_snippet,
                   1 - distance AS sim_vec,
                   ROW_NUMBER() OVER (ORDER BY distance) AS r_vec
            FROM vec_raw
        ),
        txt AS (
            SELECT
                id, text,
                SUBSTR(text, 1, 200) AS text_snippet,
                SCORE(1) AS score_txt,
                ROW_NUMBER() OVER (ORDER BY SCORE(1) DESC) AS r_txt
            FROM KNOWLEDGE_BASE
            WHERE CONTAINS(text, :kw, 1) > 0
            FETCH FIRST {per_list} ROWS ONLY
        ),
        fused AS (
            SELECT
                COALESCE(v.id, t.id) AS id,
                COALESCE(v.text_snippet, t.text_snippet) AS text_snippet,
                NVL(v.r_vec, 999999) AS r_vec,
                NVL(t.r_txt, 999999) AS r_txt,
                NVL(v.sim_vec, 0) AS sim_vec,
                NVL(t.score_txt, 0) AS score_txt
            FROM vec v
            FULL OUTER JOIN txt t ON t.id = v.id
        )
        SELECT
            id, text_snippet,
            ROUND((1.0/(:k + r_vec)) + (1.0/(:k + r_txt)), 6) AS rrf_score,
            r_vec, r_txt,
            ROUND(sim_vec, 4) AS sim_vec,
            ROUND(score_txt, 4) AS score_txt
        FROM fused
        ORDER BY rrf_score DESC
        FETCH FIRST {top_k} ROWS ONLY
    """

    return execute_query(
        conn,
        sql,
        {"q": qv, "kw": safe_kw, "k": k},
        query_logger,
        description=f"Hybrid RRF (Vector + Text fusion): '{search_phrase[:40]}'",
    )
