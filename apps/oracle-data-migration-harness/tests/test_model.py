from unittest.mock import Mock, patch

from data_migration_harness.model import complete, get_model


def test_get_model_returns_instance(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("API_KEY", "test-key")
    get_model.cache_clear()
    assert get_model() is not None


def test_complete_returns_string(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("API_KEY", "test-key")
    get_model.cache_clear()

    chunk = Mock()
    chunk.choices = [Mock(delta=Mock(content="ready"))]

    with patch("data_migration_harness.model.get_model") as mock_get_model:
        mock_client = Mock()
        mock_client.chat.completions.create.return_value = [chunk]
        mock_get_model.return_value = mock_client

        out = complete("Reply with the single word: ready")

    assert out == "ready"
