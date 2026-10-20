"""The embedding model and the indexes: loading, the hybrid index, and the setup hint."""

import pytest

from golestan_code_mcp.search import model

pytestmark = pytest.mark.needs_model  # the shared `conn` then requires the embedding model


def test_failed_download_names_the_url_and_leaves_nothing(tmp_path):
    url = "http://127.0.0.1:1/all_MiniLM_L12_v2.onnx"
    with pytest.raises(model.ModelError, match="127.0.0.1:1"):
        model.fetch_model({"CCCTX_MODEL_URL": url, "CCCTX_MODEL_CACHE": str(tmp_path)})
    assert list(tmp_path.iterdir()) == []


def test_hybrid_index_is_set_up(conn):
    with conn.cursor() as cur:
        assert ("ALL_MINILM_L12_V2",) in cur.execute("SELECT model_name FROM user_mining_models").fetchall()
        v = cur.execute("SELECT VECTOR_EMBEDDING(ALL_MINILM_L12_V2 USING 'hello world' as data) AS v").fetchone()[0]
        assert len(v) == 384
        assert cur.execute("select index_name from user_indexes where index_name = :i", i=model.INDEX).fetchone()
        assert cur.execute("select model_name, dimension from ccctx_embedding_model").fetchall() == [
            ("ALL_MINILM_L12_V2", 384)
        ]


def test_load_model_again_changes_nothing(conn):
    # an unreachable URL proves nothing is downloaded when everything is already set up
    status = model.load_model(conn, {"CCCTX_MODEL_URL": "http://127.0.0.1:1/x.onnx"})
    assert status == "model ALL_MINILM_L12_V2 already present (384 dimensions)"


def test_require_model_names_the_setup_command(conn, monkeypatch):
    monkeypatch.setattr(model, "INDEX", "NOT_AN_INDEX")
    with pytest.raises(model.ModelError, match="ccctx model load"):
        model.require_model(conn)


def test_load_model_keeps_the_page_index(conn, ledger):
    from golestan_code_mcp.wiki import store

    model.load_model(conn, {"CCCTX_MODEL_URL": "http://127.0.0.1:1/x.onnx"})
    with conn.cursor() as cur:
        assert cur.execute("select count(*) from user_indexes where index_name = :i", i=store.INDEX).fetchone()[0]
