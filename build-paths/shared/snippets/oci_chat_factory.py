"""OCI Generative AI chat client (bearer-token recipe — no OCI config needed).

WHY THIS RECIPE
---------------
OCI now ships an API-key authentication path for the Generative AI service in
us-phoenix-1: just a `Bearer sk-...` token against an OpenAI-compatible
endpoint. Verified during the build-paths friction pass: returns Grok 4
responses directly without `~/.oci/config`, without a tenancy, without
compartment OCIDs, without the SigV1 ceremony.

The earlier OCI-SDK SigV1 path still works at us-chicago-1 if you have a
tenancy; this snippet picks bearer-token-first because it removes the entire
"OCI account prerequisite" from build-paths projects — an influencer can
build a demo with just an API key, no signup flow.

USAGE
-----
    out = chat_complete([{"role": "user", "content": "Reply OK."}])
    # `out` is the assistant message text.

REQUIRED ENV
------------
OCI_GENAI_API_KEY     `sk-...` token from the OCI GenAI service console.
                      NEVER commit this to git. Load from .env (which is
                      gitignored) or your shell profile.
OCI_GENAI_BASE_URL    Defaults to
                      https://inference.generativeai.us-phoenix-1.oci.oraclecloud.com
OCI_LLM_MODEL         Defaults to xai.grok-4.

DEPS
----
openai>=1.40   (the only chat dep needed; `oci` and `oci-openai` are NOT
                used on this path)
"""

from __future__ import annotations

import os
from typing import Any

from openai import OpenAI


_chat_client: Any = None


def get_chat_client() -> OpenAI:
    """Return an OpenAI-shaped client pointing at the OCI GenAI OpenAI-compat
    endpoint. Module-scoped + cached. Auth via `OCI_GENAI_API_KEY`."""
    global _chat_client
    if _chat_client is not None:
        return _chat_client

    api_key = os.environ.get("OCI_GENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OCI_GENAI_API_KEY is required. Get one from the OCI Generative AI "
            "service console and add it to your project's .env file (which "
            "MUST be gitignored)."
        )

    base_url = os.environ.get(
        "OCI_GENAI_BASE_URL",
        "https://inference.generativeai.us-phoenix-1.oci.oraclecloud.com",
    )
    # The endpoint accepts /v1/chat/completions; the OpenAI SDK appends
    # /chat/completions automatically. So the configured base_url should
    # end at `/v1`.
    if not base_url.rstrip("/").endswith("/v1"):
        base_url = base_url.rstrip("/") + "/v1"

    _chat_client = OpenAI(base_url=base_url, api_key=api_key)
    return _chat_client


def chat_complete(
    messages: list[dict],
    temperature: float = 0.2,
    max_tokens: int = 512,
) -> str:
    """One-shot chat completion. Returns the assistant message text."""
    client = get_chat_client()
    model_id = os.environ.get("OCI_LLM_MODEL", "xai.grok-4")
    if model_id == "grok-4":
        model_id = "xai.grok-4"

    resp = client.chat.completions.create(
        model=model_id,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return resp.choices[0].message.content
