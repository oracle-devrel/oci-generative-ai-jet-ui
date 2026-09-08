"""Smoke tests for the reasoning path's vector store dispatch.

These tests catch the class of bug where reasoning code calls a method
that doesn't exist on OraDBVectorStore (e.g. the `.query()` regression
that shipped in commit 0b2c5b2). They use a FakeVectorStore that mimics
the real OraDBVectorStore public surface. Any call to an undefined
method raises AttributeError and the test fails.

Designed to run in CI without Oracle DB, Ollama, or heavy ML deps.
Only pytest is required.
"""
import asyncio
import re
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest


# Stub out agent_reasoning so rag_ensemble imports without pulling in
# the full reasoning stack. The smoke test only exercises _retrieve_context,
# which never touches ReasoningEnsemble.
def _install_agent_reasoning_stub():
    if "agent_reasoning" in sys.modules:
        return
    ar = types.ModuleType("agent_reasoning")
    ar.ReasoningEnsemble = MagicMock()
    ar_agents = types.ModuleType("agent_reasoning.agents")
    ar_agents.AGENT_MAP = {}
    sys.modules["agent_reasoning"] = ar
    sys.modules["agent_reasoning.agents"] = ar_agents


_install_agent_reasoning_stub()

# Put src/ on the path so reasoning.rag_ensemble is importable.
_SRC = Path(__file__).resolve().parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from reasoning.rag_ensemble import RAGReasoningEnsemble  # noqa: E402


class FakeVectorStore:
    """Mimics OraDBVectorStore's public query surface.

    Critically, it does NOT implement a generic `.query()` method. If
    reasoning code ever calls `vector_store.query(...)`, this fake
    raises AttributeError and the test fails loudly.
    """

    def __init__(self):
        self.calls = []

    def query_pdf_collection(self, query, n_results=3):
        self.calls.append(("pdf", query, n_results))
        return [{"content": "pdf chunk", "metadata": {"source": "a.pdf"}, "score": 0.9}]

    def query_web_collection(self, query, n_results=3):
        self.calls.append(("web", query, n_results))
        return [{"content": "web chunk", "metadata": {"source": "http://x"}, "score": 0.8}]

    def query_repo_collection(self, query, n_results=3):
        self.calls.append(("repo", query, n_results))
        return [{"content": "repo chunk", "metadata": {"source": "gh/x"}, "score": 0.7}]

    def query_general_collection(self, query, n_results=3):
        self.calls.append(("general", query, n_results))
        return [{"content": "kb chunk", "metadata": {"source": "kb"}, "score": 0.6}]


@pytest.fixture
def ensemble():
    # Bypass __init__ so we don't drag in Ollama / ReasoningEnsemble wiring.
    # _retrieve_context only touches self.vector_store.
    inst = RAGReasoningEnsemble.__new__(RAGReasoningEnsemble)
    inst.vector_store = FakeVectorStore()
    return inst


@pytest.mark.parametrize(
    "collection,expected_method",
    [
        ("PDF", "pdf"),
        ("Web", "web"),
        ("Repository", "repo"),
        ("General", "general"),
    ],
)
def test_retrieve_context_dispatches_to_correct_method(ensemble, collection, expected_method):
    """Each UI collection label must route to the matching query_*_collection method."""
    result = asyncio.run(ensemble._retrieve_context("what is RAG?", collection))
    assert result is not None, f"Expected context for collection={collection}"
    assert ensemble.vector_store.calls, "Fake vector store was never called"
    assert ensemble.vector_store.calls[0][0] == expected_method
    assert result["chunks"], "Chunks list should not be empty"
    assert result["chunks"][0]["content"]
    assert result["avg_score"] > 0


def test_retrieve_context_unknown_collection_defaults_to_pdf(ensemble):
    """Unknown collection labels fall back to PDF."""
    result = asyncio.run(ensemble._retrieve_context("test", "NotARealCollection"))
    assert result is not None
    assert ensemble.vector_store.calls[0][0] == "pdf"


def test_retrieve_context_returns_none_when_store_missing_method(ensemble):
    """If the configured store lacks the expected method, return None instead
    of raising AttributeError. This guards against future store implementations
    that forget to expose query_*_collection methods."""
    ensemble.vector_store = object()  # plain object has no query_pdf_collection
    result = asyncio.run(ensemble._retrieve_context("test", "PDF"))
    assert result is None


def test_retrieve_context_returns_none_when_no_store(ensemble):
    ensemble.vector_store = None
    result = asyncio.run(ensemble._retrieve_context("test", "PDF"))
    assert result is None


def test_no_bare_vector_store_query_calls_in_source():
    """Guard against the exact regression we fixed in commit b8101d8.

    OraDBVectorStore exposes query_pdf_collection / query_web_collection /
    query_repo_collection / query_general_collection. It has no bare `.query()`
    method. Any source file that calls `vector_store.query(` will AttributeError
    at runtime.
    """
    src_dir = Path(__file__).resolve().parent.parent / "src"
    # Match `vector_store.query(` but NOT `vector_store.query_foo(`.
    # The negative lookahead (?!_) excludes `query_pdf_collection` etc.
    pattern = re.compile(r"vector_store\.query(?!_)\s*\(")
    offenders = []
    for py_file in src_dir.rglob("*.py"):
        text = py_file.read_text(encoding="utf-8", errors="ignore")
        for match in pattern.finditer(text):
            line_no = text[: match.start()].count("\n") + 1
            offenders.append(f"{py_file.relative_to(src_dir.parent)}:{line_no}")
    assert not offenders, (
        "Found bare `vector_store.query(` calls. OraDBVectorStore has no "
        "generic query() method -- use query_pdf_collection / query_web_collection "
        f"/ query_repo_collection / query_general_collection instead. Offenders: {offenders}"
    )
