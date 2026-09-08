"""Thin Python wrapper around Oracle's VECTOR_EMBEDDING SQL function.

The actual embedding work happens in the DB against the ONNX model loaded
by `scripts/load_onnx_model.py`. No external embedding API is called.
"""

from __future__ import annotations

import os

import numpy as np

from soccer_agent.db import get_connection

_MODEL = os.environ.get("ORACLE_EMBED_MODEL", "ALL_MINILM_L6_V2")
_DIM = 384
_MAX_EMBED_WORDS = 220
_MAX_EMBED_CHARS = 1000


def _prepare_text(text: str) -> str:
    """Keep input within the ONNX tokenizer window used by Oracle."""
    cleaned = " ".join(str(text).split())
    words = cleaned.split(" ")
    if len(words) > _MAX_EMBED_WORDS:
        cleaned = " ".join(words[:_MAX_EMBED_WORDS])
    if len(cleaned) > _MAX_EMBED_CHARS:
        cleaned = cleaned[:_MAX_EMBED_CHARS].rsplit(" ", 1)[0] or cleaned[:_MAX_EMBED_CHARS]
    return cleaned


def embed_one(text: str) -> np.ndarray:
    """Embed a single string. Returns float32 ndarray of shape (384,)."""
    prepared = _prepare_text(text)
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            f"SELECT TO_VECTOR(VECTOR_EMBEDDING({_MODEL} USING :t AS DATA)) "
            "FROM DUAL", t=prepared,
        )
        vec = cur.fetchone()[0]
    return np.asarray(vec, dtype=np.float32)


def embed_many(texts: list[str]) -> np.ndarray:
    """Embed a list of strings. Returns (N, 384) float32 ndarray.

    Calls VECTOR_EMBEDDING once per row via a single SQL with a values clause.
    For demo-scale batches (hundreds) this is fast enough.
    """
    if not texts:
        return np.zeros((0, _DIM), dtype=np.float32)
    out = np.zeros((len(texts), _DIM), dtype=np.float32)
    with get_connection() as conn:
        cur = conn.cursor()
        for i, t in enumerate(texts):
            prepared = _prepare_text(t)
            cur.execute(
                f"SELECT TO_VECTOR(VECTOR_EMBEDDING({_MODEL} USING :t AS DATA)) "
                "FROM DUAL", t=prepared,
            )
            out[i, :] = np.asarray(cur.fetchone()[0], dtype=np.float32)
    return out
