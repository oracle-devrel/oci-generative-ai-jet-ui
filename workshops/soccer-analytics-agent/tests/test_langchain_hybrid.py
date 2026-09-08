from dataclasses import dataclass

import numpy as np

from soccer_agent.memory import langchain_hybrid as hybrid
from soccer_agent.memory import oracle_agent_memory as oam


def test_prediction_document_from_row_formats_model_output():
    doc = hybrid.prediction_document_from_row(
        ("Spain", "Brazil", 0.567, 0.255, 0.178, "xgb-v1")
    )

    assert doc.doc_id == "prediction:xgb-v1:Spain:Brazil"
    assert "ML prediction for Spain vs Brazil" in doc.page_content
    assert "56.7%" in doc.page_content
    assert doc.metadata["doc_type"] == "prediction"
    assert doc.metadata["favorite"] == "Spain"
    assert doc.metadata["source_table"] == "PREDICCIONES_FINAL"


def test_team_documents_carry_retrieval_metadata():
    stat = hybrid.team_stat_document_from_row(("Argentina", 90, 52, 57.78, 150, 66))
    decade = hybrid.team_decade_document_from_row(("Brazil", 1970, 12, 10, 33, 9))

    assert stat.metadata["doc_type"] == "team_stat"
    assert stat.metadata["source_view"] == "VW_TEAM_STATISTICS"
    assert "Argentina" in stat.page_content
    assert decade.metadata["doc_type"] == "team_decade"
    assert decade.metadata["decade"] == 1970
    assert "1970s FIFA World Cups" in decade.page_content


@dataclass
class _FakeDoc:
    page_content: str
    metadata: dict
    id: str | None = None


def test_rrf_merge_combines_vector_and_text_ranks():
    spain = _FakeDoc("Spain prediction evidence", {"doc_id": "prediction:Spain"})
    brazil = _FakeDoc("Brazil team facts", {"doc_id": "team_stat:Brazil"})

    results = hybrid._rrf_merge(
        [(spain, 0.12), (brazil, 0.22)],
        [spain],
        limit=2,
        note="fallback path",
    )

    assert [r.metadata["doc_id"] for r in results] == ["prediction:Spain", "team_stat:Brazil"]
    assert results[0].retrieval_mode == "fallback_rrf"
    assert results[0].metadata["vector_rank"] == 1
    assert results[0].metadata["text_rank"] == 1
    assert results[0].metadata["retrieval_note"] == "fallback path"


def test_missing_table_detection_is_narrow():
    class MissingTableError(Exception):
        def __str__(self):
            return "ORA-00942: table or view does not exist"

    class ConnectionError(Exception):
        def __str__(self):
            return "DPY-6005: cannot connect to database"

    assert hybrid._is_missing_table_error(MissingTableError())
    assert not hybrid._is_missing_table_error(ConnectionError())


def test_error_summary_is_concise_and_keeps_exception_type():
    err = RuntimeError("x" * 300)

    summary = hybrid._error_summary(err)

    assert summary.startswith("RuntimeError: ")
    assert len(summary) < 250
    assert summary.endswith("...")


def test_oracle_agent_memory_embedder_uses_database_embedding_adapter(monkeypatch):
    calls = []

    def fake_embed_many(texts):
        calls.append(texts)
        return np.ones((len(texts), 384), dtype=np.float32)

    monkeypatch.setattr(oam, "embed_many", fake_embed_many)
    embedder = oam.OracleDatabaseEmbedder()

    assert embedder.embed_query("hello") == [1.0] * 384
    matrix = embedder.embed(["a", "b"])
    assert matrix.shape == (2, 384)
    assert calls == [["hello"], ["a", "b"]]


def test_oracle_agent_memory_demo_preserves_warning_evidence(monkeypatch):
    class FakeThread:
        def add_messages(self, messages):
            raise RuntimeError("message indexing unavailable")

        def add_memory(self, text):
            self.memory = text

    class FakeMemory:
        def create_thread(self, **kwargs):
            return FakeThread()

        def search(self, **kwargs):
            return [type("Result", (), {"content": "remembered Spain evidence"})()]

    class FakeScope:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    class FakeConn:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

    monkeypatch.setattr(oam, "_imports", lambda: {"SearchScope": FakeScope})
    monkeypatch.setattr(oam, "create_memory_client", lambda conn: FakeMemory())
    monkeypatch.setattr(oam, "get_connection", lambda: FakeConn())

    result = oam.run_demo()

    assert result.retrieved == ["remembered Spain evidence"]
    assert result.warnings == [
        "thread.add_messages skipped: RuntimeError: message indexing unavailable"
    ]
