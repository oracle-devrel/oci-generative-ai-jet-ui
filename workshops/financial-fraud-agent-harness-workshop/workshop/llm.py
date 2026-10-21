"""Chat LLM setup: credentials from the environment and an OpenAI-compatible `chat()` helper."""
import getpass
import os
import sys
import time
from pathlib import Path

from openai import OpenAI, RateLimitError


def _import_key_rotation():
    root = next((p for p in [Path.cwd(), *Path.cwd().parents]
                 if (p / "oci_key_rotation.py").exists()), None)
    if root is None:
        raise RuntimeError("Run this notebook from the workshop repository")
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    import oci_key_rotation
    return oci_key_rotation


def configure_llm():
    """Read or prompt for credentials. Returns (provider, router).

    `router` is the OCI `ModelRouter` (model fallback chain, silent), or None for the OpenAI provider.
    """
    kr = _import_key_rotation()
    provider = os.environ.setdefault("LLM_PROVIDER", "oci").lower()
    assert provider in ("openai", "oci"), "LLM_PROVIDER must be 'openai' or 'oci'"
    router = None
    if provider == "oci":
        if not kr.load_keys("OCI_GENAI_API_KEY"):
            os.environ["OCI_GENAI_API_KEY"] = getpass.getpass("OCI GenAI API key: ")
        os.environ.setdefault("LLM_MODEL", "xai.grok-4.3")
        router = kr.ModelRouter(kr.load_lanes())
    else:
        if not os.environ.get("OPENAI_API_KEY"):
            os.environ["OPENAI_API_KEY"] = getpass.getpass("OpenAI API key: ")
        os.environ.setdefault("LLM_MODEL", "gpt-5.5")
    print(f"LLM: {provider}/{os.environ['LLM_MODEL']}")
    return provider, router


RATE_LIMIT_BACKOFF = (15, 30, 60)   # seconds before retries 1-3; a Retry-After header wins


def _retry_rate_limit(call):
    """OpenAI provider only: retry a 429 up to three times with backoff and one short line per retry."""
    for delay in (*RATE_LIMIT_BACKOFF, None):
        try:
            return call()
        except RateLimitError as exc:
            if delay is None:
                raise
            try:
                delay = min(float(exc.response.headers["retry-after"]), 120.0)
            except (AttributeError, KeyError, TypeError, ValueError):
                pass
            print(f"  rate-limited, retrying in {delay:.0f} s")
            time.sleep(delay)


def make_chat(provider, model, router=None):
    """Build the chat client and a `chat(messages, tools=None)` function. Returns (llm, chat).

    With OCI, every call goes through the router (rate-limit/outage fallback, no output).
    """
    llm = router if provider == "oci" else OpenAI(api_key=os.environ["OPENAI_API_KEY"])

    def chat(messages, tools=None, model=model):
        kwargs = {"model": model, "messages": messages}
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"
        if provider == "oci":
            return router.chat(**kwargs)
        return _retry_rate_limit(lambda: llm.chat.completions.create(**kwargs))

    return llm, chat


def check_bare_question(question, answer):
    """Checkpoint for TODO 1: a bank-data question was asked and the bare model answered."""
    assert question.strip(), "❌ TODO 1: set QUESTION to a question first."
    assert any(w in question.lower() for w in ("meridian", "finance", "customer", "account", "transaction", "alert")), \
        "❌ TODO 1: ask about Meridian Bank data (a customer, account, transaction or alert)."
    assert answer, "❌ TODO 1: the model returned no answer. Check your key and LLM_MODEL."
    print("✅ TODO 1 passed: the bare model answered, with no access to the bank data.")
