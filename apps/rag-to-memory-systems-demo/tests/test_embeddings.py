"""Tests for the ONNX embedding model and SQL embedding helper."""
import pytest

from memory.db import connect_sync
from memory.embeddings import MODEL_NAME, VECTOR_DIM, vector_embedding_sql


def _model_is_loaded() -> bool:
    """Return True iff the ONNX model exists in the database."""
    try:
        conn = connect_sync()
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT COUNT(*) FROM all_mining_models WHERE model_name = :name",
                name=MODEL_NAME,
            )
            (count,) = cur.fetchone()
            return count > 0
        finally:
            conn.close()
    except Exception:
        return False


def test_vector_embedding_sql_format():
    assert vector_embedding_sql() == f"VECTOR_EMBEDDING({MODEL_NAME} USING :text AS DATA)"


def test_model_loaded_and_embeds_text():
    conn = connect_sync()
    try:
        cur = conn.cursor()
        cur.execute(
            f"SELECT {vector_embedding_sql(':t')} FROM dual",
            t="customer support",
        )
        (vec,) = cur.fetchone()
        assert len(vec) == VECTOR_DIM
    finally:
        conn.close()
