"""
Pydantic models for OpenAI-compatible API.

These models define the request/response format for the OpenAI-compatible
endpoints that Open WebUI and other clients can consume.
"""

from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field
from enum import Enum
import time
import uuid


class MessageRole(str, Enum):
    """Role of a message in a conversation."""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    FUNCTION = "function"
    TOOL = "tool"


class ContentPart(BaseModel):
    """A single part of multimodal content."""
    type: str  # "text", "image_url", "file", etc.
    text: Optional[str] = None
    image_url: Optional[Dict[str, Any]] = None  # {"url": "...", "detail": "..."}
    file: Optional[Dict[str, Any]] = None  # For file attachments
    # Additional fields that might come from Open WebUI
    id: Optional[str] = None
    name: Optional[str] = None
    data: Optional[str] = None  # Base64 encoded content
    url: Optional[str] = None  # URL for web content


class FileAttachment(BaseModel):
    """File attachment format used by Open WebUI."""
    type: str = "file"  # "file", "image", "collection", etc.
    id: Optional[str] = None
    name: Optional[str] = None
    filename: Optional[str] = None
    url: Optional[str] = None
    data: Optional[str] = None  # Base64 encoded content
    collection_name: Optional[str] = None
    # Additional metadata
    size: Optional[int] = None
    content_type: Optional[str] = None


class ChatMessage(BaseModel):
    """A single message in a chat conversation."""
    role: MessageRole
    # Content can be string OR array of content parts (multimodal)
    content: Optional[Union[str, List[ContentPart]]] = None
    name: Optional[str] = None
    function_call: Optional[Dict[str, Any]] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    # Additional fields for attachments/images
    images: Optional[List[str]] = None  # Base64 or URLs


class ChatCompletionRequest(BaseModel):
    """Request body for /v1/chat/completions endpoint."""
    model: str = Field(..., description="Model ID to use (e.g., 'cot-rag', 'tot')")
    messages: List[ChatMessage] = Field(..., description="List of messages in the conversation")
    stream: bool = Field(default=True, description="Whether to stream the response")
    temperature: Optional[float] = Field(default=0.7, ge=0.0, le=2.0)
    top_p: Optional[float] = Field(default=1.0, ge=0.0, le=1.0)
    n: Optional[int] = Field(default=1, ge=1, le=10)
    max_tokens: Optional[int] = Field(default=None)
    presence_penalty: Optional[float] = Field(default=0.0, ge=-2.0, le=2.0)
    frequency_penalty: Optional[float] = Field(default=0.0, ge=-2.0, le=2.0)
    stop: Optional[Union[str, List[str]]] = None
    user: Optional[str] = None

    # Additional fields that some clients may send
    logit_bias: Optional[Dict[str, float]] = None
    response_format: Optional[Dict[str, str]] = None
    seed: Optional[int] = None
    tools: Optional[List[Dict[str, Any]]] = None
    tool_choice: Optional[Union[str, Dict[str, Any]]] = None

    # Open WebUI specific fields for file/document attachments
    files: Optional[List[FileAttachment]] = None
    # Additional Open WebUI fields
    chat_id: Optional[str] = None
    session_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class ChatCompletionChoice(BaseModel):
    """A single choice in a chat completion response."""
    index: int = 0
    message: ChatMessage
    finish_reason: Optional[str] = "stop"
    logprobs: Optional[Dict[str, Any]] = None


class UsageInfo(BaseModel):
    """Token usage information."""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class ChatCompletionResponse(BaseModel):
    """Response body for /v1/chat/completions (non-streaming)."""
    id: str = Field(default_factory=lambda: f"chatcmpl-{uuid.uuid4().hex[:12]}")
    object: str = "chat.completion"
    created: int = Field(default_factory=lambda: int(time.time()))
    model: str
    choices: List[ChatCompletionChoice]
    usage: Optional[UsageInfo] = None
    system_fingerprint: Optional[str] = None


class DeltaContent(BaseModel):
    """Delta content for streaming responses."""
    role: Optional[str] = None
    content: Optional[str] = None
    function_call: Optional[Dict[str, Any]] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None


class ChatCompletionChunkChoice(BaseModel):
    """A single choice in a streaming chunk."""
    index: int = 0
    delta: DeltaContent
    finish_reason: Optional[str] = None
    logprobs: Optional[Dict[str, Any]] = None


class ChatCompletionChunk(BaseModel):
    """Streaming chunk for /v1/chat/completions."""
    id: str
    object: str = "chat.completion.chunk"
    created: int
    model: str
    choices: List[ChatCompletionChunkChoice]
    system_fingerprint: Optional[str] = None


class ModelInfo(BaseModel):
    """Information about a single model."""
    id: str
    object: str = "model"
    created: int = Field(default_factory=lambda: int(time.time()))
    owned_by: str = "agentic-rag"
    # Extended fields for display
    name: Optional[str] = None
    description: Optional[str] = None


class ModelList(BaseModel):
    """Response body for /v1/models endpoint."""
    object: str = "list"
    data: List[ModelInfo]


class ErrorDetail(BaseModel):
    """Error detail in API responses."""
    message: str
    type: str = "invalid_request_error"
    param: Optional[str] = None
    code: Optional[str] = None


class ErrorResponse(BaseModel):
    """Error response format."""
    error: ErrorDetail


# Model registry with all 18 reasoning models
REASONING_MODELS: Dict[str, Dict[str, Any]] = {
    "standard": {
        "strategy": "standard",
        "rag": False,
        "name": "Standard",
        "description": "Standard response without specialized reasoning"
    },
    "standard-rag": {
        "strategy": "standard",
        "rag": True,
        "name": "Standard + RAG",
        "description": "Standard response with RAG context from all collections"
    },
    "cot": {
        "strategy": "cot",
        "rag": False,
        "name": "Chain of Thought",
        "description": "Step-by-step reasoning process"
    },
    "cot-rag": {
        "strategy": "cot",
        "rag": True,
        "name": "Chain of Thought + RAG",
        "description": "Step-by-step reasoning with RAG context"
    },
    "tot": {
        "strategy": "tot",
        "rag": False,
        "name": "Tree of Thoughts",
        "description": "Explores multiple reasoning paths in parallel"
    },
    "tot-rag": {
        "strategy": "tot",
        "rag": True,
        "name": "Tree of Thoughts + RAG",
        "description": "Tree exploration with RAG context"
    },
    "react": {
        "strategy": "react",
        "rag": False,
        "name": "ReAct",
        "description": "Reasoning and Acting interleaved approach"
    },
    "react-rag": {
        "strategy": "react",
        "rag": True,
        "name": "ReAct + RAG",
        "description": "ReAct with RAG context"
    },
    "self-reflection": {
        "strategy": "self_reflection",
        "rag": False,
        "name": "Self-Reflection",
        "description": "Iterative self-critique and refinement"
    },
    "self-reflection-rag": {
        "strategy": "self_reflection",
        "rag": True,
        "name": "Self-Reflection + RAG",
        "description": "Self-reflection with RAG context"
    },
    "consistency": {
        "strategy": "consistency",
        "rag": False,
        "name": "Self-Consistency",
        "description": "Multiple samples with majority voting"
    },
    "consistency-rag": {
        "strategy": "consistency",
        "rag": True,
        "name": "Self-Consistency + RAG",
        "description": "Self-consistency with RAG context"
    },
    "decomposed": {
        "strategy": "decomposed",
        "rag": False,
        "name": "Decomposed",
        "description": "Breaks complex problems into sub-problems"
    },
    "decomposed-rag": {
        "strategy": "decomposed",
        "rag": True,
        "name": "Decomposed + RAG",
        "description": "Decomposition with RAG context"
    },
    "least-to-most": {
        "strategy": "least_to_most",
        "rag": False,
        "name": "Least-to-Most",
        "description": "Solves from simplest to most complex"
    },
    "least-to-most-rag": {
        "strategy": "least_to_most",
        "rag": True,
        "name": "Least-to-Most + RAG",
        "description": "Least-to-most with RAG context"
    },
    "recursive": {
        "strategy": "recursive",
        "rag": False,
        "name": "Recursive",
        "description": "Recursive problem decomposition"
    },
    "recursive-rag": {
        "strategy": "recursive",
        "rag": True,
        "name": "Recursive + RAG",
        "description": "Recursive reasoning with RAG context"
    },
}


def get_model_list() -> ModelList:
    """Get the list of available models."""
    models = []
    for model_id, config in REASONING_MODELS.items():
        models.append(ModelInfo(
            id=model_id,
            name=config["name"],
            description=config.get("description")
        ))
    return ModelList(data=models)


def get_model_config(model_id: str) -> Optional[Dict[str, Any]]:
    """Get configuration for a specific model."""
    return REASONING_MODELS.get(model_id)
