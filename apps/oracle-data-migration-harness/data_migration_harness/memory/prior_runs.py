"""Layer 5: prior-run memory via langchain-oracledb.

Uses sentence-transformers locally for embeddings (no API call), matching the
embedding model used everywhere else in the project so retrieval is consistent
with the migrated RAG corpus.
"""

import os
from functools import lru_cache

from langchain_oracledb.vectorstores import OracleVS
from sentence_transformers import SentenceTransformer

from data_migration_harness.environment import oracle_pool


class LocalSTEmbeddings:
    """Minimal LangChain-compatible embedding wrapper around sentence-transformers."""

    def __init__(self, model_name: str):
        self._model = SentenceTransformer(model_name)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [vec.tolist() for vec in self._model.encode(texts, normalize_embeddings=True)]

    def embed_query(self, text: str) -> list[float]:
        return self._model.encode([text], normalize_embeddings=True)[0].tolist()


@lru_cache(maxsize=1)
def _embeddings() -> LocalSTEmbeddings:
    return LocalSTEmbeddings(
        os.environ.get("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    )


@lru_cache(maxsize=1)
def get_run_memory() -> OracleVS:
    """Returns a singleton OracleVS instance backed by the agent_run_memory table.

    Passes the pool directly so OracleVS manages connection checkout internally.
    This avoids a leaked acquired connection on each process start.
    """
    return OracleVS(
        client=oracle_pool(),
        embedding_function=_embeddings(),
        table_name="agent_run_memory",
    )


def record_run_summary(text: str, metadata: dict) -> None:
    """Store a run summary as a vector document for later similarity retrieval.

    Args:
        text: Free-text description of what the agent run did.
        metadata: Arbitrary key/value pairs (e.g. run_id, timestamp, side).

    Returns:
        None
    """
    get_run_memory().add_texts([text], metadatas=[metadata])


def find_similar_runs(query: str, k: int = 3):
    """Return the k most similar prior run summaries for a given query.

    Args:
        query: Natural-language description of the current task.
        k: Number of results to return.

    Returns:
        List of LangChain Document objects with page_content and metadata.
    """
    return get_run_memory().similarity_search(query, k=k)
