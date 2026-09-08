"""Integration test: RAGReasoningEnsemble._retrieve_context against a real
Oracle DB.

This is the test that would have caught the `.query()` regression (fixed
in commit b8101d8) BEFORE it shipped. The smoke test catches it at the
source-scan level; this one catches it at the runtime level against a real
vector store.

What this catches:
- Any dispatch regression in _retrieve_context
- Schema mismatches between rag_ensemble expectations and OraDBVectorStore
- Return-shape drift (chunks/sources/avg_score keys)
"""
import asyncio

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.requires_oracle]


@pytest.fixture
def ensemble_with_real_store(oracle_vector_store):
    """Construct a RAGReasoningEnsemble bypassing __init__ so we don't pull
    in the full reasoning stack. We only exercise _retrieve_context, which
    only needs self.vector_store to be set."""
    # Seed a chunk so queries have something to retrieve.
    oracle_vector_store.add_pdf_chunks(
        [
            {
                "text": "RAG stands for Retrieval Augmented Generation, "
                "a technique where an LLM retrieves relevant context "
                "before generating an answer.",
                "metadata": {"source": "reasoning_integration_test", "page": 1},
            }
        ],
        document_id="reasoning_test_doc",
    )

    from reasoning.rag_ensemble import RAGReasoningEnsemble

    inst = RAGReasoningEnsemble.__new__(RAGReasoningEnsemble)
    inst.vector_store = oracle_vector_store
    return inst


def test_retrieve_context_against_real_pdf_collection(ensemble_with_real_store):
    """The PDF path runs end-to-end against the real Oracle DB."""
    result = asyncio.run(
        ensemble_with_real_store._retrieve_context("What is RAG?", "PDF")
    )
    assert result is not None, "Expected retrieval to return a context dict"
    assert "chunks" in result
    assert "sources" in result
    assert "avg_score" in result
    assert len(result["chunks"]) >= 1
    first = result["chunks"][0]
    assert first["content"], "Chunks should have non-empty content"
    assert isinstance(first["metadata"], dict)


@pytest.mark.parametrize("collection", ["PDF", "Web", "Repository", "General"])
def test_retrieve_context_never_raises_for_valid_collections(
    ensemble_with_real_store, collection
):
    """All four UI collection labels must complete without raising.
    Collections other than PDF may return empty -- that's fine, the point
    is the dispatch doesn't blow up with AttributeError."""
    try:
        asyncio.run(ensemble_with_real_store._retrieve_context("test", collection))
    except AttributeError as e:
        pytest.fail(
            f"_retrieve_context raised AttributeError for collection={collection}: {e}. "
            "This is the regression class that caused commit b8101d8."
        )
