import numpy as np
import pytest

from soccer_agent.agent.embeddings import embed_one, embed_many


def test_embed_one_truncates_long_input(monkeypatch):
    captured = {}

    class Cursor:
        def execute(self, _sql, **kwargs):
            captured["text"] = kwargs["t"]

        def fetchone(self):
            return [[0.0] * 384]

    class Connection:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def cursor(self):
            return Cursor()

    monkeypatch.setattr(
        "soccer_agent.agent.embeddings.get_connection", lambda: Connection(),
    )

    v = embed_one("word " * 700)

    assert v.shape == (384,)
    assert len(captured["text"].split()) <= 220
    assert len(captured["text"]) <= 1000


@pytest.mark.integration
def test_embed_one_returns_384(onnx_model_loaded):
    v = embed_one("Spain won the 2010 World Cup.")
    assert v.shape == (384,) and v.dtype == np.float32


@pytest.mark.integration
def test_embed_many_returns_n_by_384(onnx_model_loaded):
    m = embed_many(["alpha", "beta", "gamma"])
    assert m.shape == (3, 384)


@pytest.mark.integration
def test_embed_many_distinct_inputs_differ(onnx_model_loaded):
    m = embed_many(["football is great", "soccer is the same sport"])
    assert not np.allclose(m[0], m[1])
