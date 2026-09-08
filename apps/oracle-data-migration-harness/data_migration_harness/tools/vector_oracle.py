"""Layer 3: Oracle vector search using VECTOR column on the products table.

Uses 384-dim FLOAT32 vectors to match sentence-transformers/all-MiniLM-L6-v2,
the local embedding model the project uses (per Casius's environment deltas).
"""

import array as _array

from data_migration_harness.environment import oracle_pool


def add_vector_column():
    pool = oracle_pool()
    with pool.acquire() as conn:
        cur = conn.cursor()
        for stmt in (
            "ALTER TABLE products ADD (review_embedding VECTOR(384, FLOAT32))",
            "ALTER TABLE products ADD (review_text VARCHAR2(2000))",
        ):
            try:
                cur.execute(stmt)
            except Exception:
                pass
        conn.commit()


def write_embeddings(rows: list[tuple[str, str, list[float]]]):
    """Write review text and embedding vectors into the products table.

    Args:
        rows: A list of (mongo_id, review_text, embedding) tuples.
              embedding must be 384-dimensional to match VECTOR(384, FLOAT32).

    Returns:
        None

    Example:
        >>> write_embeddings([("6612...", "Great product", [0.1, 0.2, ...])])
    """
    pool = oracle_pool()
    with pool.acquire() as conn:
        cur = conn.cursor()
        # Named binds are required for VECTOR columns: oracledb's executemany
        # with positional binds (:1/:2/:3) tries to use the VECTOR value as a
        # deduplication comparison key and raises ORA-22848. Named binds bypass
        # that code path entirely.
        bound_rows = [
            {"mid": mongo_id, "txt": text, "emb": _array.array("f", embedding)}
            for mongo_id, text, embedding in rows
        ]
        cur.executemany(
            "UPDATE products SET review_text = :txt, review_embedding = :emb WHERE mongo_id = :mid",
            bound_rows,
        )
        conn.commit()


def vector_search_oracle(query_embedding: list[float], k: int = 5) -> list[dict]:
    """Find the k most similar products by cosine distance on review_embedding.

    Args:
        query_embedding: 384-dimensional query vector (FLOAT32).
        k: Number of nearest neighbours to return.

    Returns:
        A list of dicts with keys: name, category, review_text, distance.

    Example:
        >>> results = vector_search_oracle([0.1, 0.2, ...], k=3)
    """
    pool = oracle_pool()
    with pool.acquire() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT name, category, review_text,
                   VECTOR_DISTANCE(review_embedding, :qv, COSINE) AS distance
            FROM products
            WHERE review_embedding IS NOT NULL
            ORDER BY distance
            FETCH FIRST :k ROWS ONLY
            """,
            {
                "qv": _array.array("f", query_embedding),
                "k": k,
            },
        )
        cols = [c[0].lower() for c in cur.description]
        return [dict(zip(cols, row, strict=False)) for row in cur.fetchall()]
