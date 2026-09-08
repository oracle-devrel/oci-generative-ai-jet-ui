"""ONNX embedding model registration.

The model is loaded into Oracle once via DBMS_VECTOR.LOAD_ONNX_MODEL.
After that, embedding happens in SQL via VECTOR_EMBEDDING.

Uses the L12 augmented variant distributed by Oracle via OML AI Models object storage.
Both L6 and L12 produce 384-dimensional embeddings.
"""
from __future__ import annotations

MODEL_NAME = "ALL_MINILM_L12_V2"
VECTOR_DIM = 384


def vector_embedding_sql(text_bind: str = ":text") -> str:
    """Returns a SQL fragment that embeds a bind variable's text.
    Use inside INSERTs and SELECTs in place of a pre-computed vector."""
    return f"VECTOR_EMBEDDING({MODEL_NAME} USING {text_bind} AS DATA)"
