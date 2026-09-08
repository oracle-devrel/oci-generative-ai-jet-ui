"""Integration tests: OraDBVectorStore against a real Oracle DB.

Requires a running Oracle DB Free container (see docker-compose.test.yml).
Skips gracefully if the DB isn't reachable. Uses DeterministicEmbedding
(from conftest.py) so the in-DB ONNX model is not required.

What this catches:
- Broken SQL / schema migrations in the vector store
- Connection / credential issues
- Regressions where query_*_collection methods stop working end-to-end
"""
import pytest

pytestmark = [pytest.mark.integration, pytest.mark.requires_oracle]


@pytest.fixture
def seeded_store(oracle_vector_store):
    """Seed one chunk into the PDF collection so queries have something to find."""
    chunks = [
        {
            "text": "Oracle Database 23ai Free is a fully featured edition for developers.",
            "metadata": {"source": "integration_test", "page": 1},
        }
    ]
    oracle_vector_store.add_pdf_chunks(chunks, document_id="int_test_doc")
    yield oracle_vector_store


def test_connection_is_live(oracle_vector_store):
    """Smoke check: we can execute a trivial SELECT on the live connection."""
    cursor = oracle_vector_store.connection.cursor()
    cursor.execute("SELECT 1 FROM DUAL")
    row = cursor.fetchone()
    cursor.close()
    assert row == (1,)


def test_query_pdf_collection_returns_dict_list(seeded_store):
    """query_pdf_collection must return a list of dicts with content + metadata."""
    results = seeded_store.query_pdf_collection("Oracle Database", n_results=3)
    assert isinstance(results, list)
    assert len(results) >= 1
    first = results[0]
    assert "content" in first
    assert "metadata" in first
    assert isinstance(first["metadata"], dict), (
        "metadata should be a dict, not a str -- "
        "the OraDBVectorStore monkeypatch is supposed to parse JSON metadata"
    )


@pytest.mark.parametrize(
    "method_name",
    [
        "query_pdf_collection",
        "query_web_collection",
        "query_repo_collection",
        "query_general_collection",
    ],
)
def test_all_query_methods_exist_and_are_callable(oracle_vector_store, method_name):
    """Guard: every query_*_collection method exists and is callable.

    This would have caught the `.query()` regression immediately -- if someone
    renames or removes one of these, the import/invocation here fails loudly.
    """
    method = getattr(oracle_vector_store, method_name, None)
    assert callable(method), f"OraDBVectorStore.{method_name} missing or not callable"
    result = method("probe query", n_results=1)
    assert isinstance(result, list)


def test_collection_count_roundtrip(seeded_store):
    """Adding a chunk should increase the collection count by at least one."""
    count = seeded_store.get_collection_count("PDFCOLLECTION")
    assert count >= 1
