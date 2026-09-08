"""Tests for OllamaClient."""

import json
from unittest.mock import MagicMock, patch

import pytest
import requests as real_requests

from agent_reasoning.client import OllamaClient


def _make_client():
    """Create an OllamaClient with explicit base_url (skips config)."""
    return OllamaClient(model="test-model", base_url="http://localhost:11434")


class TestOllamaClient:
    @patch("agent_reasoning.client.requests")
    def test_generate_streaming(self, mock_req):
        """Streaming generate should yield chunks."""
        client = _make_client()
        lines = [
            json.dumps({"response": "Hello", "done": False}).encode(),
            json.dumps({"response": " world", "done": False}).encode(),
            json.dumps({"response": "", "done": True}).encode(),
        ]
        mock_response = MagicMock()
        mock_response.iter_lines.return_value = lines
        mock_response.raise_for_status = MagicMock()
        mock_req.post.return_value = mock_response

        chunks = list(client.generate("test prompt"))
        # The done=True chunk yields its (empty) response before breaking
        assert chunks == ["Hello", " world", ""]

    @patch("agent_reasoning.client.requests")
    def test_generate_non_streaming(self, mock_req):
        """Non-streaming generate should yield single response."""
        client = _make_client()
        mock_response = MagicMock()
        mock_response.json.return_value = {"response": "Full response"}
        mock_response.raise_for_status = MagicMock()
        mock_req.post.return_value = mock_response

        chunks = list(client.generate("test", stream=False))
        assert chunks == ["Full response"]

    @patch("agent_reasoning.client.requests")
    def test_generate_connection_error(self, mock_req):
        """Connection errors should yield error message, not crash."""
        client = _make_client()
        mock_req.post.side_effect = real_requests.exceptions.ConnectionError("Connection refused")
        mock_req.exceptions = real_requests.exceptions

        chunks = list(client.generate("test"))
        assert len(chunks) == 1
        assert "Error" in chunks[0]

    @patch("agent_reasoning.client.requests")
    def test_generate_passes_stop_tokens(self, mock_req):
        """Stop tokens should be passed to the API."""
        client = _make_client()
        mock_response = MagicMock()
        mock_response.json.return_value = {"response": "ok"}
        mock_response.raise_for_status = MagicMock()
        mock_req.post.return_value = mock_response

        list(client.generate("test", stream=False, stop=["Observation:"]))
        call_data = mock_req.post.call_args[1]["json"]
        assert call_data["stop"] == ["Observation:"]

    @patch("agent_reasoning.client.requests")
    def test_generate_passes_system_prompt(self, mock_req):
        """System prompt should be passed to the API."""
        client = _make_client()
        mock_response = MagicMock()
        mock_response.json.return_value = {"response": "ok"}
        mock_response.raise_for_status = MagicMock()
        mock_req.post.return_value = mock_response

        list(client.generate("test", stream=False, system="You are helpful"))
        call_data = mock_req.post.call_args[1]["json"]
        assert call_data["system"] == "You are helpful"

    @patch("agent_reasoning.client.requests")
    def test_generate_default_params(self, mock_req):
        """Default parameters should be set correctly."""
        client = _make_client()
        mock_response = MagicMock()
        mock_response.json.return_value = {"response": "ok"}
        mock_response.raise_for_status = MagicMock()
        mock_req.post.return_value = mock_response

        list(client.generate("test", stream=False))
        call_data = mock_req.post.call_args[1]["json"]
        assert call_data["temperature"] == 0.7
        assert call_data["top_k"] == 40
        assert call_data["top_p"] == 0.9
        assert call_data["num_predict"] == 2048

    @patch("agent_reasoning.client.requests")
    def test_generate_no_stop_when_none(self, mock_req):
        """Stop tokens should NOT be in the payload when not provided."""
        client = _make_client()
        mock_response = MagicMock()
        mock_response.json.return_value = {"response": "ok"}
        mock_response.raise_for_status = MagicMock()
        mock_req.post.return_value = mock_response

        list(client.generate("test", stream=False))
        call_data = mock_req.post.call_args[1]["json"]
        assert "stop" not in call_data

    @patch("agent_reasoning.client.requests")
    def test_generate_no_system_when_none(self, mock_req):
        """System prompt should NOT be in the payload when not provided."""
        client = _make_client()
        mock_response = MagicMock()
        mock_response.json.return_value = {"response": "ok"}
        mock_response.raise_for_status = MagicMock()
        mock_req.post.return_value = mock_response

        list(client.generate("test", stream=False))
        call_data = mock_req.post.call_args[1]["json"]
        assert "system" not in call_data

    @patch("agent_reasoning.client.requests")
    def test_generate_uses_correct_url(self, mock_req):
        """Should POST to /api/generate on the configured base_url."""
        client = _make_client()
        mock_response = MagicMock()
        mock_response.json.return_value = {"response": "ok"}
        mock_response.raise_for_status = MagicMock()
        mock_req.post.return_value = mock_response

        list(client.generate("test", stream=False))
        url = mock_req.post.call_args[0][0]
        assert url == "http://localhost:11434/api/generate"

    @patch("agent_reasoning.client.requests")
    def test_generate_sends_model_name(self, mock_req):
        """Should include the model name in the request payload."""
        client = _make_client()
        mock_response = MagicMock()
        mock_response.json.return_value = {"response": "ok"}
        mock_response.raise_for_status = MagicMock()
        mock_req.post.return_value = mock_response

        list(client.generate("test", stream=False))
        call_data = mock_req.post.call_args[1]["json"]
        assert call_data["model"] == "test-model"

    @patch("agent_reasoning.client.requests")
    def test_generate_sends_prompt(self, mock_req):
        """Should include the prompt text in the request payload."""
        client = _make_client()
        mock_response = MagicMock()
        mock_response.json.return_value = {"response": "ok"}
        mock_response.raise_for_status = MagicMock()
        mock_req.post.return_value = mock_response

        list(client.generate("my custom prompt", stream=False))
        call_data = mock_req.post.call_args[1]["json"]
        assert call_data["prompt"] == "my custom prompt"

    @patch("agent_reasoning.client.requests")
    def test_generate_streaming_done_behavior(self, mock_req):
        """Streaming yields content from done=True chunk, then stops."""
        client = _make_client()
        lines = [
            json.dumps({"response": "only chunk", "done": False}).encode(),
            json.dumps({"response": "also yielded", "done": True}).encode(),
        ]
        mock_response = MagicMock()
        mock_response.iter_lines.return_value = lines
        mock_response.raise_for_status = MagicMock()
        mock_req.post.return_value = mock_response

        chunks = list(client.generate("test"))
        # The code yields content THEN checks done, so both appear
        assert "only chunk" in chunks
        assert "also yielded" in chunks
        assert len(chunks) == 2

    @patch("agent_reasoning.client.requests")
    def test_generate_empty_response_field(self, mock_req):
        """Non-streaming with empty response should yield empty string."""
        client = _make_client()
        mock_response = MagicMock()
        mock_response.json.return_value = {}
        mock_response.raise_for_status = MagicMock()
        mock_req.post.return_value = mock_response

        chunks = list(client.generate("test", stream=False))
        assert chunks == [""]

    @patch("agent_reasoning.client.requests")
    def test_generate_custom_temperature(self, mock_req):
        """Custom temperature should override the default."""
        client = _make_client()
        mock_response = MagicMock()
        mock_response.json.return_value = {"response": "ok"}
        mock_response.raise_for_status = MagicMock()
        mock_req.post.return_value = mock_response

        list(client.generate("test", stream=False, temperature=0.2))
        call_data = mock_req.post.call_args[1]["json"]
        assert call_data["temperature"] == 0.2

    @patch("agent_reasoning.client.requests")
    def test_generate_http_error(self, mock_req):
        """HTTP errors (non-connection) should also yield error message."""
        client = _make_client()
        mock_req.post.side_effect = real_requests.exceptions.HTTPError("500 Server Error")
        mock_req.exceptions = real_requests.exceptions

        chunks = list(client.generate("test"))
        assert len(chunks) == 1
        assert "Error" in chunks[0]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
