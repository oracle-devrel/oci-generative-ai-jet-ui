"""Register an ONNX embedding model in Oracle via DBMS_VECTOR.LOAD_ONNX_MODEL.

Source: ~/git/personal/onnx2oracle/src/onnx2oracle/loader.py:15-70

WHY THIS EXISTS
---------------
Once an ONNX model is registered, Oracle can produce embeddings inside SQL via
`VECTOR_EMBEDDING(model_name USING text AS data)` — no Python embedder process,
no network round-trips per query. The loader is idempotent: if the model is
already registered, it's a no-op.

CONSTRAINTS (cannot be relaxed):
  * ONNX opset must be ≤ 14 (Oracle's runtime is pinned).
  * Tokenizer must be BertTokenizer-family. SentencePiece (T5, XLM-R) fails
    at LOAD_ONNX_MODEL or at first inference.
  * Model file must live on a path the DB can read. The skill creates an
    Oracle DIRECTORY object pointing at the host path before calling this.

USAGE
-----
    register_onnx_model(
        conn,
        directory_name="ONNX_DIR",
        file_name="all-MiniLM-L6-v2.onnx",
        model_name="MY_MINILM",
    )
    # Then in SQL:
    #   SELECT VECTOR_EMBEDDING(MY_MINILM USING 'hi' AS data) FROM dual;
"""

from __future__ import annotations

import json

import oracledb


def model_exists(conn: oracledb.Connection, model_name: str) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) FROM USER_MINING_MODELS WHERE model_name = :n",
            n=model_name.upper(),
        )
        return cur.fetchone()[0] > 0


def register_onnx_model(
    conn: oracledb.Connection,
    directory_name: str,
    file_name: str,
    model_name: str,
    *,
    force: bool = False,
) -> None:
    """Idempotently load an ONNX model. Pass force=True to drop and reload."""
    if model_exists(conn, model_name):
        if not force:
            return
        with conn.cursor() as cur:
            cur.execute("BEGIN DBMS_VECTOR.DROP_ONNX_MODEL(:m); END;",
                        m=model_name.upper())
        conn.commit()

    metadata = json.dumps({
        "function": "embedding",
        "embeddingOutput": "embedding",
        "input": {"input": ["DATA"]},
    })

    with conn.cursor() as cur:
        cur.execute(
            """
            BEGIN
              DBMS_VECTOR.LOAD_ONNX_MODEL(
                directory => :dir,
                file_name => :fn,
                model_name => :mn,
                metadata => JSON(:md)
              );
            END;
            """,
            dir=directory_name,
            fn=file_name,
            mn=model_name,
            md=metadata,
        )
    conn.commit()
