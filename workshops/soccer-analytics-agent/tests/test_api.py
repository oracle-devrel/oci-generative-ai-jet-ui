from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(memory_schema_ready, onnx_model_loaded):
    from soccer_agent.api.main import app
    return TestClient(app)


@pytest.mark.integration
def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["oracle"] is True


def test_health_grok_configured_requires_all_three_vars(monkeypatch):
    """grok_configured is False unless all three OCI env vars are set."""
    from soccer_agent.api.main import app
    from fastapi.testclient import TestClient

    # Patch oracle check to avoid needing a live DB for this unit test.
    monkeypatch.setattr("soccer_agent.api.main.get_connection",
                        lambda: _NullCtx())

    for missing in ("OCI_GENAI_MODEL_ID", "OCI_GENAI_API_KEY", "OCI_GENAI_ENDPOINT"):
        monkeypatch.setenv("OCI_GENAI_MODEL_ID", "xai.grok-4")
        monkeypatch.setenv("OCI_GENAI_API_KEY", "sk-test")
        monkeypatch.setenv("OCI_GENAI_ENDPOINT", "https://example.oci.com")
        monkeypatch.delenv(missing, raising=False)
        r = TestClient(app).get("/health")
        assert r.json()["grok_configured"] is False, f"expected False when {missing} is missing"

    # All three set → True.
    monkeypatch.setenv("OCI_GENAI_MODEL_ID", "xai.grok-4")
    monkeypatch.setenv("OCI_GENAI_API_KEY", "sk-test")
    monkeypatch.setenv("OCI_GENAI_ENDPOINT", "https://example.oci.com")
    r = TestClient(app).get("/health")
    assert r.json()["grok_configured"] is True


class _NullCtx:
    """Minimal context manager that returns a fake Oracle connection."""

    def __enter__(self):
        return _FakeConn()

    def __exit__(self, *_):
        pass


class _FakeConn:
    def cursor(self):
        return _FakeCursor()


class _FakeCursor:
    def execute(self, *_):
        return self

    def fetchone(self):
        return (1,)


@pytest.mark.integration
def test_chat_no_tool_call(client):
    from soccer_agent.agent.grok_client import GrokReply
    with patch("soccer_agent.agent.loop.grok_chat") as mock:
        mock.return_value = GrokReply(text="hi", tool_calls=[], raw=None)
        r = client.post("/chat", json={"message": "hello"})
    assert r.status_code == 200
    body = r.json()
    assert body["reply"] == "hi"
    assert "session_id" in body
    assert body["tool_trace"] == []


def test_predict_endpoint_uses_live_features(client, monkeypatch):
    from soccer_agent.inference.bulk import Prediction

    captured = {}

    class Runtime:
        def build_feature_row(self, home_team, away_team, *, neutral=True):
            captured["teams"] = (home_team, away_team, neutral)
            return {"home_elo": 2200.0, "away_elo": 2050.0}

    def fake_live_predict(features, home_team, away_team):
        captured["features"] = features
        return Prediction(home_team, away_team, 0.56, 0.25, 0.19, "live", "live")

    monkeypatch.setattr("soccer_agent.api.main.get_runtime", lambda: Runtime())
    monkeypatch.setattr("soccer_agent.api.main.live_predict", fake_live_predict)

    r = client.post("/predict", json={"home_team": "Spain", "away_team": "Brazil"})
    assert r.status_code == 200
    body = r.json()
    assert body["prob_home_win"] == pytest.approx(0.56)
    assert body["source"] == "live"
    assert body["features_used"] == 2
    assert captured["teams"] == ("Spain", "Brazil", True)
    assert captured["features"] == {"home_elo": 2200.0, "away_elo": 2050.0}


def test_chat_endpoint_returns_json_on_failure(client, monkeypatch):
    def fail_turn(*_args, **_kwargs):
        raise RuntimeError("simulated failure")

    monkeypatch.setattr("soccer_agent.api.main.run_turn", fail_turn)

    r = client.post("/chat", json={"message": "hello"})

    assert r.status_code == 500
    assert r.headers["content-type"].startswith("application/json")
    body = r.json()
    assert body["error_type"] == "RuntimeError"
    assert body["detail"] == "simulated failure"
    assert "session_id" in body


@pytest.mark.integration
def test_memory_get_and_delete(client):
    from soccer_agent.agent.grok_client import GrokReply
    with patch("soccer_agent.agent.loop.grok_chat") as mock:
        mock.return_value = GrokReply(text="hi", tool_calls=[], raw=None)
        r = client.post("/chat", json={"message": "first"})
        sid = r.json()["session_id"]
        client.post("/chat", json={"session_id": sid, "message": "second"})

    r = client.get(f"/memory/{sid}")
    assert r.status_code == 200
    assert len(r.json()["turns"]) >= 4   # 2 user + 2 assistant

    r = client.delete(f"/memory/{sid}")
    assert r.status_code == 200
    r = client.get(f"/memory/{sid}")
    assert r.json()["turns"] == []
