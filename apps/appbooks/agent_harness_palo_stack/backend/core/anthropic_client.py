"""Shared Anthropic clients. Uses a placeholder key when unset so the app still
imports and serves the frontend (API calls then fail with a clear error)."""
from __future__ import annotations

import anthropic

from backend.config import settings

_key = settings.anthropic_api_key or "ANTHROPIC_API_KEY_NOT_SET"
client = anthropic.Anthropic(api_key=_key)
async_client = anthropic.AsyncAnthropic(api_key=_key)
MODEL = settings.model
MAX_TOKENS = settings.max_tokens


def text_of(response) -> str:
    return "".join(b.text for b in response.content if getattr(b, "type", None) == "text")
