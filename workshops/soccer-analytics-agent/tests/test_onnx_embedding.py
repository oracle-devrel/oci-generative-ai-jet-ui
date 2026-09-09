import pytest
from soccer_agent.db import get_connection


@pytest.mark.integration
def test_in_db_embedding_returns_384_dims(onnx_model_loaded):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT TO_VECTOR(VECTOR_EMBEDDING(ALL_MINILM_L6_V2 USING :t AS DATA)) FROM DUAL",
            t="Spain won the 2010 World Cup.",
        )
        vec = cur.fetchone()[0]
    assert len(vec) == 384
