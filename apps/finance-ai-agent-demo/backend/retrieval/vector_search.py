"""Semantic vector similarity search using HNSW index."""

import array

from database.query_helper import execute_query


def vector_search(conn, embedding_model, query, top_k=5, query_logger=None):
    """Semantic vector similarity search on KNOWLEDGE_BASE."""
    query_embedding = embedding_model.embed_query(query)
    query_array = array.array("f", query_embedding)

    # NOTE: oracledb thin mode misinterprets vector binds when the SELECT clause
    # wraps columns in functions (TO_CHAR, SUBSTR, ROUND, arithmetic).  Use a
    # subquery: inner query selects raw columns (matching langchain's pattern),
    # outer query applies transformations on already-fetched rows.
    sql = f"""
        SELECT id, text,
               SUBSTR(text, 1, 200) AS text_snippet,
               ROUND(1 - distance, 4) AS similarity_score
        FROM (
            SELECT id, text, metadata,
                   vector_distance(embedding, :q, COSINE) as distance
            FROM KNOWLEDGE_BASE
            ORDER BY distance
            FETCH APPROX FIRST {top_k} ROWS ONLY WITH TARGET ACCURACY 90
        )
        ORDER BY distance
    """

    return execute_query(
        conn, sql, {"q": query_array}, query_logger, description=f"Vector search: '{query[:50]}'"
    )
