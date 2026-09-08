"""In-DB ONNX embeddings: a LangChain Embeddings subclass that calls
`VECTOR_EMBEDDING(<MODEL_NAME> USING :t AS data) FROM dual` via SQL.

WHY THIS EXISTS
---------------
At intermediate / advanced tiers, we register an ONNX model inside Oracle
(via `onnx2oracle` per friction P0-4) and let the database produce
embeddings. This subclass adapts that to LangChain's `Embeddings` interface
so `OracleVS` (or any LangChain retriever) can use it without thinking.

Same MiniLM-L6-v2 model as the beginner's Python-side `HuggingFaceEmbeddings`,
just with inference happening inside Oracle. 384 dim. The corpus chunk-size
sweet spot stays the same across tiers — only the embedding location changes.

USAGE
-----
    from .store import get_connection
    embedder = InDBEmbeddings(get_connection(), model_db_name="MY_MINILM_V1")
    qv = embedder.embed_query("hello")  # -> list[float] length 384

    # Or with OracleVS:
    vs = OracleVS(client=conn, embedding_function=embedder,
                  table_name="DOCS", distance_strategy=DistanceStrategy.COSINE)
"""

from __future__ import annotations

import json
from typing import List

import oracledb
from langchain_core.embeddings import Embeddings


class InDBEmbeddings(Embeddings):
    """LangChain Embeddings backed by Oracle's `VECTOR_EMBEDDING` SQL function."""

    def __init__(
        self,
        conn: oracledb.Connection,
        model_db_name: str = "MY_MINILM_V1",
    ):
        self.conn = conn
        self.model_db_name = model_db_name

    def _embed_one(self, text: str) -> List[float]:
        """Round-trip one string through Oracle's VECTOR_EMBEDDING.

        Oracle returns the vector as an `array.array('f', [...])`-shaped
        VECTOR; we convert to a plain `list[float]` for LangChain compat."""
        with self.conn.cursor() as cur:
            cur.execute(
                f"SELECT VECTOR_EMBEDDING({self.model_db_name} USING :t AS data) "
                f"FROM dual",
                t=text,
            )
            (vec,) = cur.fetchone()
        # `vec` may be a list, an array.array, or a JSON-encoded string
        # depending on driver mode. Normalise.
        if hasattr(vec, "tolist"):
            return list(vec.tolist())
        if isinstance(vec, (bytes, bytearray)):
            return json.loads(vec.decode("utf-8"))
        if isinstance(vec, str):
            return json.loads(vec)
        return list(vec)

    def embed_query(self, text: str) -> List[float]:
        return self._embed_one(text)

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [self._embed_one(t) for t in texts]
