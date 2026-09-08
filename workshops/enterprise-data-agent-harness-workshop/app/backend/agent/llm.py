"""Chat-completion client with automatic OCI → OpenAI fallback.

Mirrors the notebook's §3.3 wiring but with two production-grade additions:

  1. OCI is *attempted first* whenever OCI_GENAI_API_KEY is present and the
     endpoint normalizes to a valid OpenAI-compatible URL. If the very first
     request fails (401, 404, network), we transparently switch to OpenAI
     gpt-5.5 (configurable via LLM_FALLBACK_MODEL) for the rest of the
     process. We don't flap back to OCI within a session.
  2. If OCI credentials are absent/malformed at boot, we go straight to
     OpenAI without even trying OCI. This means a misconfigured .env doesn't
     break startup — the chat just runs against the fallback.

The router exposes the same `client.chat.completions.create(...)` shape the
existing call sites rely on, so harness.py / events.py don't change.
"""

from __future__ import annotations

import time

from openai import (
    OpenAI,
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    NotFoundError,
)

from config import (
    LLM_FALLBACK_MODEL,
    LLM_MODEL,
    LLM_PROVIDER,
    OCI_API_KEY_WAS_CLEANED,
    OCI_ENDPOINT_WAS_CLEANED,
    OCI_GENAI_API_KEY,
    OCI_GENAI_API_KEY_RAW,
    OCI_GENAI_ENDPOINT,
    OCI_GENAI_ENDPOINT_RAW,
    OPENAI_API_KEY,
)


# Exceptions that should trigger the OCI → OpenAI fallback. We treat all
# of these as "OCI is unusable for this session" rather than transient.
_FALLBACK_ERRORS = (
    AuthenticationError,
    NotFoundError,
    APIConnectionError,
    APITimeoutError,
)


class _Provider:
    """One concrete chat provider — either OCI or OpenAI direct."""

    def __init__(self, label: str, model: str, client: OpenAI):
        self.label = label
        self.model = model
        self.client = client

    def __repr__(self) -> str:
        return f"<Provider {self.label} model={self.model}>"


class LlmRouter:
    """OCI-first / OpenAI-fallback router with the OpenAI SDK's `chat`
    interface, so existing call sites can use it as a drop-in client.

    `router.chat.completions.create(model=..., messages=..., tools=...)`
    routes to the active provider. On a fallback-worthy error (auth, 404,
    connection), the router records the failure, switches to the OpenAI
    fallback if available, and replays the call. The model name in `kwargs`
    is rewritten to match the active provider so the caller doesn't need to
    care which one is actually serving the request.
    """

    def __init__(self):
        self.primary: _Provider | None = None
        self.fallback: _Provider | None = None
        self._using_fallback = False
        self._build()

        # The .chat.completions.create surface — wired below.
        self.chat = _ChatNamespace(self)

    # ----- construction -----

    def _build(self) -> None:
        # Primary: OCI iff LLM_PROVIDER asks for it AND we have credentials.
        if LLM_PROVIDER == "oci" and OCI_GENAI_API_KEY and OCI_GENAI_ENDPOINT:
            try:
                client = OpenAI(api_key=OCI_GENAI_API_KEY, base_url=OCI_GENAI_ENDPOINT)
                self.primary = _Provider("oci", LLM_MODEL, client)
                self._log_oci_setup()
            except Exception as e:
                print(f"[llm] OCI primary client could NOT be constructed: "
                      f"{type(e).__name__}: {e}")
                self.primary = None

        # Fallback: OpenAI direct on gpt-5.5 (or whatever LLM_FALLBACK_MODEL is).
        if OPENAI_API_KEY:
            self.fallback = _Provider(
                "openai", LLM_FALLBACK_MODEL, OpenAI(api_key=OPENAI_API_KEY),
            )

        # If we have no primary, promote the fallback.
        if self.primary is None and self.fallback is not None:
            print(f"[llm] No OCI credentials — using OpenAI {self.fallback.model} as primary.")
            self.primary = self.fallback
            self.fallback = None
            self._using_fallback = False

        # If we have a primary and LLM_PROVIDER asked for openai, use it
        # (don't keep an unused fallback around).
        if LLM_PROVIDER == "openai" and self.primary and self.primary.label == "openai":
            self.fallback = None

        if self.primary is None:
            raise RuntimeError(
                "No usable LLM credentials — set OPENAI_API_KEY (preferred) "
                "and/or OCI_GENAI_API_KEY + OCI_GENAI_ENDPOINT in .env."
            )

    def _log_oci_setup(self) -> None:
        print(f"[llm] OCI primary configured: model={LLM_MODEL} endpoint={OCI_GENAI_ENDPOINT}")
        if OCI_API_KEY_WAS_CLEANED:
            print(f"[llm]   note: OCI_GENAI_API_KEY was sanitized "
                  f"(saw {len(OCI_GENAI_API_KEY_RAW)} chars; using first key after splitting on ' and '/','/';').")
        if OCI_ENDPOINT_WAS_CLEANED:
            print(f"[llm]   note: OCI_GENAI_ENDPOINT was normalized "
                  f"({OCI_GENAI_ENDPOINT_RAW!r} → {OCI_GENAI_ENDPOINT!r}).")
        if self.fallback:
            print(f"[llm]   fallback ready: openai/{self.fallback.model} (kicks in on auth/404/network errors).")

    # ----- routing -----

    def active_provider(self) -> _Provider:
        return self.fallback if (self._using_fallback and self.fallback) else self.primary

    def info(self) -> dict:
        ap = self.active_provider()
        return {
            "active_label": ap.label,
            "active_model": ap.model,
            "primary_label": self.primary.label if self.primary else None,
            "fallback_label": self.fallback.label if self.fallback else None,
            "using_fallback": self._using_fallback,
        }

    def _create(self, **kwargs) -> object:
        """Run the call against whichever provider is active. On a
        fallback-worthy error against the primary, switch and retry."""
        provider = self.active_provider()
        # Always rewrite the model to match the active provider so callers
        # that hard-code LLM_MODEL still get routed correctly.
        kwargs["model"] = provider.model

        try:
            return provider.client.chat.completions.create(**kwargs)
        except _FALLBACK_ERRORS as e:
            # Only swap if we have somewhere to swap TO, and we haven't
            # already moved off the primary.
            if not self._using_fallback and self.fallback is not None:
                print(f"[llm] {provider.label} ({provider.model}) failed: "
                      f"{type(e).__name__}: {str(e)[:140]} — switching to "
                      f"{self.fallback.label} ({self.fallback.model}) for the rest of the session.")
                self._using_fallback = True
                kwargs["model"] = self.fallback.model
                return self.fallback.client.chat.completions.create(**kwargs)
            raise


class _ChatNamespace:
    """Lets call sites do `router.chat.completions.create(...)`."""
    def __init__(self, router: "LlmRouter"):
        self.completions = _CompletionsNamespace(router)


class _CompletionsNamespace:
    def __init__(self, router: "LlmRouter"):
        self._router = router

    def create(self, **kwargs):
        return self._router._create(**kwargs)


def build_llm_client() -> LlmRouter:
    """Drop-in replacement for the prior build_llm_client(). Returns the
    router; callers continue using `client.chat.completions.create(...)`.
    """
    return LlmRouter()


def chat_with_retry(client: LlmRouter, messages: list, tools: list | None = None,
                    max_retries: int = 3, model: str | None = None):
    """Retry on HTTP 429 with exponential backoff.

    `model` is accepted for backward compatibility but ignored — the router
    picks the model based on which provider is currently active. This means
    a single chat_with_retry call can transparently start on OCI and
    finish on OpenAI gpt-5.5 if OCI dies mid-turn.
    """
    delay = 1.0
    for attempt in range(max_retries):
        try:
            kwargs = {"messages": messages}
            if tools:
                kwargs["tools"] = tools
            return client.chat.completions.create(**kwargs)
        except APIStatusError as e:
            if attempt < max_retries - 1 and getattr(e, "status_code", 0) == 429:
                time.sleep(delay)
                delay *= 2
                continue
            raise
        except Exception as e:
            msg = str(e).lower()
            if attempt < max_retries - 1 and ("429" in msg or "rate" in msg):
                time.sleep(delay)
                delay *= 2
                continue
            raise
    raise RuntimeError("unreachable")
