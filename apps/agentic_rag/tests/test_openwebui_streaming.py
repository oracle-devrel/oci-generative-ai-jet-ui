"""
Tests for OpenWebUI streaming responses.

This test suite verifies that:
1. The FastAPI backend responds correctly to chat completions
2. Streaming responses are properly formatted
3. Open WebUI can receive and display responses

Run with: pytest tests/test_openwebui_streaming.py -v
"""

import json
from concurrent.futures import ThreadPoolExecutor

import pytest
import requests

# Backend configuration
BACKEND_URL = "http://localhost:8000"
TIMEOUT = 60  # seconds


def _backend_reachable() -> bool:
    """Check if the backend server is reachable."""
    try:
        requests.get(f"{BACKEND_URL}/v1/health", timeout=2)
        return True
    except Exception:
        return False


pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not _backend_reachable(), reason="Backend not running at localhost:8000"),
]


class TestBackendHealth:
    """Test backend health and availability."""

    def test_health_endpoint(self):
        """Test that the health endpoint returns correct status."""
        response = requests.get(f"{BACKEND_URL}/v1/health", timeout=10)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["models_available"] > 0, "No models available"
        assert data["vector_store_available"] is True, "Vector store not available"

    def test_models_endpoint(self):
        """Test that models endpoint returns available models."""
        response = requests.get(f"{BACKEND_URL}/v1/models", timeout=10)
        assert response.status_code == 200
        data = response.json()
        assert data["object"] == "list"
        assert len(data["data"]) > 0, "No models returned"

        # Check for essential models
        model_ids = [m["id"] for m in data["data"]]
        assert "standard" in model_ids, "Standard model not available"
        assert "cot" in model_ids, "CoT model not available"


class TestNonStreamingChatCompletions:
    """Test non-streaming chat completions."""

    def test_basic_completion(self):
        """Test basic non-streaming chat completion."""
        payload = {
            "model": "standard",
            "messages": [{"role": "user", "content": "What is 2+2?"}],
            "stream": False
        }

        response = requests.post(
            f"{BACKEND_URL}/v1/chat/completions",
            json=payload,
            timeout=TIMEOUT
        )

        assert response.status_code == 200, f"Request failed: {response.text}"
        data = response.json()

        # Validate response structure
        assert "id" in data, "Missing id in response"
        assert data["object"] == "chat.completion"
        assert "choices" in data
        assert len(data["choices"]) > 0

        choice = data["choices"][0]
        assert "message" in choice
        assert choice["message"]["role"] == "assistant"
        assert choice["message"]["content"], "Empty response content"
        assert choice["finish_reason"] == "stop"

    def test_invalid_model(self):
        """Test request with invalid model returns proper error."""
        payload = {
            "model": "nonexistent-model",
            "messages": [{"role": "user", "content": "Hello"}],
            "stream": False
        }

        response = requests.post(
            f"{BACKEND_URL}/v1/chat/completions",
            json=payload,
            timeout=10
        )

        assert response.status_code == 400
        data = response.json()
        assert "error" in data or "detail" in data


class TestStreamingChatCompletions:
    """Test streaming chat completions."""

    def _consume_stream(self, response) -> list[dict]:
        """Consume SSE stream and return parsed chunks."""
        chunks = []
        for line in response.iter_lines(decode_unicode=True):
            if line:
                if line.startswith("data: "):
                    data_str = line[6:]
                    if data_str == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data_str)
                        chunks.append(chunk)
                    except json.JSONDecodeError:
                        pass
        return chunks

    def test_streaming_completion(self):
        """Test streaming chat completion returns proper SSE chunks."""
        payload = {
            "model": "standard",
            "messages": [{"role": "user", "content": "Say hello in one word."}],
            "stream": True
        }

        response = requests.post(
            f"{BACKEND_URL}/v1/chat/completions",
            json=payload,
            stream=True,
            timeout=TIMEOUT
        )

        assert response.status_code == 200, f"Request failed: {response.text}"
        assert "text/event-stream" in response.headers.get("content-type", "")

        chunks = self._consume_stream(response)

        assert len(chunks) > 0, "No chunks received"

        # First chunk should have role
        first_chunk = chunks[0]
        assert "choices" in first_chunk
        assert first_chunk["choices"][0]["delta"].get("role") == "assistant"

        # Collect content from all chunks
        content_parts = []
        for chunk in chunks:
            delta = chunk["choices"][0].get("delta", {})
            if "content" in delta and delta["content"]:
                content_parts.append(delta["content"])

        full_content = "".join(content_parts)
        assert len(full_content) > 0, "Empty streaming response"

    def test_streaming_has_done_marker(self):
        """Test that streaming response ends with [DONE] marker."""
        payload = {
            "model": "standard",
            "messages": [{"role": "user", "content": "Hi"}],
            "stream": True
        }

        response = requests.post(
            f"{BACKEND_URL}/v1/chat/completions",
            json=payload,
            stream=True,
            timeout=TIMEOUT
        )

        assert response.status_code == 200

        lines = list(response.iter_lines(decode_unicode=True))
        # Filter non-empty lines
        data_lines = [line for line in lines if line and line.startswith("data:")]

        assert len(data_lines) > 0, "No data lines received"
        assert "data: [DONE]" in lines or any(line.strip() == "data: [DONE]" for line in lines), \
            "Missing [DONE] marker"

    def test_streaming_chunk_format(self):
        """Test that each streaming chunk has correct OpenAI format."""
        payload = {
            "model": "standard",
            "messages": [{"role": "user", "content": "What is 1+1?"}],
            "stream": True
        }

        response = requests.post(
            f"{BACKEND_URL}/v1/chat/completions",
            json=payload,
            stream=True,
            timeout=TIMEOUT
        )

        chunks = self._consume_stream(response)

        for chunk in chunks:
            # Required fields
            assert "id" in chunk, "Chunk missing id"
            assert "object" in chunk, "Chunk missing object"
            assert chunk["object"] == "chat.completion.chunk"
            assert "created" in chunk, "Chunk missing created"
            assert "model" in chunk, "Chunk missing model"
            assert "choices" in chunk, "Chunk missing choices"

            # Choice structure
            choice = chunk["choices"][0]
            assert "index" in choice
            assert "delta" in choice


class TestDifferentModels:
    """Test different reasoning models."""

    @pytest.mark.parametrize("model", ["standard", "cot", "tot", "react"])
    def test_model_responds(self, model):
        """Test that each model can generate a response."""
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": "Hello"}],
            "stream": False
        }

        try:
            response = requests.post(
                f"{BACKEND_URL}/v1/chat/completions",
                json=payload,
                timeout=TIMEOUT
            )

            assert response.status_code == 200, f"Model {model} failed: {response.text}"
            data = response.json()
            assert data["choices"][0]["message"]["content"], f"Model {model} returned empty response"
        except requests.exceptions.Timeout:
            pytest.fail(f"Model {model} timed out after {TIMEOUT}s")


class TestConcurrentRequests:
    """Test handling of concurrent requests."""

    def test_concurrent_streaming_requests(self):
        """Test that multiple concurrent streaming requests work correctly."""
        def make_request(query: str) -> dict:
            payload = {
                "model": "standard",
                "messages": [{"role": "user", "content": query}],
                "stream": True
            }
            response = requests.post(
                f"{BACKEND_URL}/v1/chat/completions",
                json=payload,
                stream=True,
                timeout=TIMEOUT
            )
            content_parts = []
            for line in response.iter_lines(decode_unicode=True):
                if line and line.startswith("data: "):
                    data_str = line[6:]
                    if data_str == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data_str)
                        delta = chunk["choices"][0].get("delta", {})
                        if "content" in delta and delta["content"] is not None:
                            content_parts.append(delta["content"])
                    except json.JSONDecodeError:
                        pass
            return {"query": query, "response": "".join(content_parts)}

        queries = ["Hello", "What is 2+2?", "Say yes"]

        with ThreadPoolExecutor(max_workers=3) as executor:
            results = list(executor.map(make_request, queries))

        for result in results:
            assert result["response"], f"Empty response for query: {result['query']}"


class TestOpenWebUICompatibility:
    """Test specific Open WebUI compatibility requirements."""

    def test_cors_headers(self):
        """Test that CORS headers are properly set."""
        response = requests.options(
            f"{BACKEND_URL}/v1/chat/completions",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST"
            },
            timeout=10
        )

        # Check CORS headers
        assert "access-control-allow-origin" in response.headers or \
               response.headers.get("access-control-allow-origin") == "*"

    def test_openai_compatible_error_format(self):
        """Test that errors follow OpenAI error format."""
        payload = {
            "model": "invalid-model-xyz",
            "messages": [{"role": "user", "content": "Hello"}],
            "stream": False
        }

        response = requests.post(
            f"{BACKEND_URL}/v1/chat/completions",
            json=payload,
            timeout=10
        )

        assert response.status_code >= 400
        data = response.json()

        # OpenAI error format
        assert "error" in data or "detail" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
