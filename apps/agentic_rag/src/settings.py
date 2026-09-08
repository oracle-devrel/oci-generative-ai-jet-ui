"""
Settings API for Agentic RAG System.

Provides endpoints to configure:
- Active LLM model (default: qwen3.5:9b)
- Model parameters
- System preferences
"""
import os
from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/v1/settings", tags=["Settings"])


class ModelSetting(BaseModel):
    model_name: str
    description: Optional[str] = None

    model_config = {"protected_namespaces": ()}


class SettingsResponse(BaseModel):
    model: ModelSetting
    available_models: List[str]


class UpdateModelRequest(BaseModel):
    model_name: str

    model_config = {"protected_namespaces": ()}


_current_settings = {
    "model_name": os.getenv("DEFAULT_MODEL", "qwen3.5:9b"),
}
_on_model_change_callbacks = []


def register_model_change_callback(callback):
    """Register a callback to be called when model changes."""
    _on_model_change_callbacks.append(callback)


def get_current_model():
    """Get the current active model name."""
    return _current_settings["model_name"]


def set_current_model(model_name):
    """Set the current active model name and notify callbacks."""
    _current_settings["model_name"] = model_name
    for callback in _on_model_change_callbacks:
        try:
            callback(model_name)
        except Exception as e:
            print(f"⚠️ Model change callback error: {e}")


def get_available_ollama_models():
    """Get list of available Ollama models."""
    try:
        import ollama

        models_response = ollama.list()
        model_list = (
            models_response.models
            if hasattr(models_response, "models")
            else models_response.get("models", [])
        )
        available = []
        for model in model_list:
            if hasattr(model, "model"):
                available.append(model.model)
            elif isinstance(model, dict) and "name" in model:
                available.append(model["name"])
            else:
                available.append(str(model))
        return available
    except Exception as e:
        print(f"⚠️ Could not list Ollama models: {e}")
        return [_current_settings["model_name"]]


@router.get("", response_model=SettingsResponse)
async def get_settings():
    """Get current settings including active model and available models."""
    available_models = get_available_ollama_models()
    return SettingsResponse(
        model=ModelSetting(
            model_name=_current_settings["model_name"],
            description=f"Currently using {_current_settings['model_name']} for reasoning",
        ),
        available_models=available_models,
    )


@router.get("/model")
async def get_current_model_endpoint():
    """Get the current active model."""
    return {"model_name": _current_settings["model_name"]}


@router.put("/model")
async def update_model(request: UpdateModelRequest):
    """Update the active LLM model."""
    old_model = _current_settings["model_name"]
    set_current_model(request.model_name)
    return {
        "success": True,
        "previous_model": old_model,
        "current_model": request.model_name,
        "message": f"Model updated from {old_model} to {request.model_name}",
    }


@router.get("/models")
async def list_available_models():
    """List all available Ollama models."""
    models = get_available_ollama_models()
    return {
        "models": models,
        "count": len(models),
        "current": _current_settings["model_name"],
    }


@router.post("/test-model")
async def test_model(request: UpdateModelRequest):
    """Test if a model is available and working."""
    try:
        import ollama

        response = ollama.chat(
            model=request.model_name,
            messages=[{"role": "user", "content": "Say hello in one word."}],
        )
        return {
            "success": True,
            "model": request.model_name,
            "response": response.get("message", {}).get("content", ""),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Model test failed: {str(e)}")
