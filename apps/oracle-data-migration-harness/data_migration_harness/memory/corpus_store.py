"""Layer 5: the migrated RAG corpus on Oracle.

Thin wrapper over the Oracle vector tool so the chat handler does not have
to know about the underlying SQL.
"""

from data_migration_harness.tools.vector_oracle import vector_search_oracle


def search_migrated_corpus(query_embedding: list[float], k: int = 5):
    """Search the migrated review corpus by vector similarity.

    Args:
        query_embedding: 384-dimensional query vector matching the
                         sentence-transformers/all-MiniLM-L6-v2 embedding space.
        k: Number of nearest neighbours to return.

    Returns:
        List of dicts with keys: name, category, review_text, distance.
    """
    return vector_search_oracle(query_embedding, k=k)
