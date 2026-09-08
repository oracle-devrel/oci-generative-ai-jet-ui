"""
Tests for Settings API.

Uses FastAPI TestClient so no running server is needed.

Run with: pytest tests/test_settings_api.py -v
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from src.settings import router

# Minimal test app with just the settings router.
_test_app = FastAPI()
_test_app.include_router(router)
client = TestClient(_test_app)


class TestSettingsAPI:
    """Test settings API endpoints."""

    def test_get_settings(self):
        """Test getting current settings."""
        response = client.get("/v1/settings")
        assert response.status_code == 200

        data = response.json()
        assert "model" in data
        assert "available_models" in data
        assert "model_name" in data["model"]

    def test_get_current_model(self):
        """Test getting current model."""
        response = client.get("/v1/settings/model")
        assert response.status_code == 200

        data = response.json()
        assert "model_name" in data
        assert data["model_name"]  # Should not be empty

    def test_list_available_models(self):
        """Test listing available Ollama models."""
        response = client.get("/v1/settings/models")
        assert response.status_code == 200

        data = response.json()
        assert "models" in data
        assert "count" in data
        assert "current" in data

    def test_update_model(self):
        """Test updating the active model (PUT endpoint)."""
        # Get current model first
        current_response = client.get("/v1/settings/model")
        current_model = current_response.json()["model_name"]

        # Update to a different model
        new_model = "gemma3:270m"
        response = client.put(
            "/v1/settings/model",
            json={"model_name": new_model},
        )
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert data["current_model"] == new_model

        # Verify it changed
        verify_response = client.get("/v1/settings/model")
        assert verify_response.json()["model_name"] == new_model

        # Restore original model
        client.put(
            "/v1/settings/model",
            json={"model_name": current_model},
        )

    def test_test_model_endpoint(self, ollama_available):
        """Test the model testing endpoint (requires Ollama)."""
        if not ollama_available:
            pytest.skip("Ollama not available")
        response = client.post(
            "/v1/settings/test-model",
            json={"model_name": "gemma3:270m"},
        )
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert data["model"] == "gemma3:270m"
        assert "response" in data

    def test_invalid_model_test(self, ollama_available):
        """Test model testing with invalid model (requires Ollama)."""
        if not ollama_available:
            pytest.skip("Ollama not available")
        response = client.post(
            "/v1/settings/test-model",
            json={"model_name": "nonexistent-model-xyz"},
        )
        assert response.status_code == 400


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
