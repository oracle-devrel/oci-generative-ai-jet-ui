"""Chat-completion client: the app's view of the shared ModelRouter.

Lanes (oci_key_rotation.load_lanes): grok-phx -> grok-chi -> gptoss-chi.
Rate limits cool a lane and move on to the next one; auth errors rotate keys
inside a lane; the switch is invisible to the UI and only logged (JSON log
file + one `[llm-router]` console line for the instructor).

One router per process (chat + OAMP extraction share its cooldown state).
"""

from __future__ import annotations

import threading

import config  # noqa: F401  (puts oci_key_rotation on sys.path, normalizes env)
from config import OCI_API_KEY_WAS_CLEANED, OCI_ENDPOINT_WAS_CLEANED
from oci_key_rotation import ModelRouter, load_lanes

_ROUTER: ModelRouter | None = None
_LOCK = threading.Lock()


def get_router() -> ModelRouter:
    """Process-wide router, or None-free: raises if no lane is configured."""
    global _ROUTER
    with _LOCK:
        if _ROUTER is None:
            lanes = load_lanes()
            if not lanes:
                raise RuntimeError(
                    "No usable LLM credentials — set OCI_GENAI_API_KEY + "
                    "OCI_GENAI_ENDPOINT in .env."
                )
            _ROUTER = ModelRouter(lanes, console=True)
            print(f"[llm] lanes: {', '.join(l.name for l in lanes)} "
                  f"(primary model={_ROUTER.primary_model})")
            if OCI_API_KEY_WAS_CLEANED:
                print("[llm]   note: OCI_GENAI_API_KEY was sanitized (multi-key string split).")
            if OCI_ENDPOINT_WAS_CLEANED:
                print("[llm]   note: OCI_GENAI_ENDPOINT was normalized to the /openai/v1 form.")
        return _ROUTER


def build_llm_client() -> ModelRouter:
    return get_router()


def chat_with_retry(client: ModelRouter, messages: list, tools: list | None = None):
    """One chat completion through the router, which owns all retry/failover."""
    kwargs = {"messages": messages}
    if tools:
        kwargs["tools"] = tools
    return client.chat(**kwargs)
