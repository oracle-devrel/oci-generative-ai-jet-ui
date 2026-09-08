"""Integration test: real Ollama inference.

Requires `ollama serve` running locally (or OLLAMA_HOST set) and the
OLLAMA_TEST_MODEL (default gemma3:270m) already pulled, or pullable
at test-run time.

What this catches:
- Ollama client wiring changes (base URL, SDK method signatures)
- Model name format drift (e.g. gemma3:270m → gemma3:270m-instruct)
- Any regression that breaks LocalRAGAgent's inference path
"""
import pytest

pytestmark = [pytest.mark.integration, pytest.mark.requires_ollama]


def test_ollama_generate_roundtrip(ollama_test_model, ollama_host):
    """Send a trivial prompt through the raw Ollama HTTP API."""
    import json
    import urllib.request

    req = urllib.request.Request(
        f"{ollama_host}/api/generate",
        data=json.dumps(
            {
                "model": ollama_test_model,
                "prompt": "Respond with exactly the word: OK",
                "stream": False,
                "options": {"temperature": 0, "num_predict": 8},
            }
        ).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        payload = json.loads(r.read())

    assert "response" in payload
    assert payload["response"].strip(), "Ollama returned an empty response"
    assert payload.get("done") is True


def test_ollama_python_sdk_list(ollama_test_model, ollama_host):
    """ollama.list() reports the test model as present."""
    try:
        import ollama
    except ImportError:
        pytest.skip("ollama Python SDK not installed")

    client = ollama.Client(host=ollama_host)
    tags = client.list()
    # SDK >= 0.4 returns a ListResponse; older returns dict.
    models = getattr(tags, "models", None) or tags.get("models", [])
    names = []
    for m in models:
        name = getattr(m, "model", None) or (m.get("model") if isinstance(m, dict) else None) or m.get("name", "")
        names.append(name)
    assert any(ollama_test_model in n for n in names), f"{ollama_test_model} not in {names}"
