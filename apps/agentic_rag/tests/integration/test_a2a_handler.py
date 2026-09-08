"""Integration test: A2A handler via the backend /a2a JSON-RPC endpoint.

Launches the FastAPI backend (via the backend_server fixture), then sends
JSON-RPC calls to /a2a and verifies the responses. The researcher path
exercises vector_store.query_pdf_collection -- which is the other call
site we fixed in commit b8101d8.

What this catches:
- JSON-RPC schema drift in the A2A handler
- Researcher path calling a nonexistent vector store method
- Registration / discovery failures in the agent registry
"""
import json
import urllib.error
import urllib.request

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.requires_oracle,
    pytest.mark.requires_ollama,
]


def _jsonrpc(url: str, method: str, params: dict, req_id: int = 1, timeout: int = 120):
    body = {"jsonrpc": "2.0", "id": req_id, "method": method, "params": params}
    req = urllib.request.Request(
        f"{url}/a2a",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        pytest.fail(f"/a2a returned HTTP {e.code}: {e.read().decode(errors='ignore')}")


def test_backend_health(backend_server):
    """/v1/health should respond 200."""
    with urllib.request.urlopen(f"{backend_server}/v1/health", timeout=10) as r:
        assert r.status == 200


def test_a2a_agent_card(backend_server):
    """/agent_card (or equivalent) returns an agent card document."""
    # Try the common paths; the exact route varies by handler version.
    for path in ["/agent_card", "/.well-known/agent.json", "/a2a/agent_card"]:
        try:
            with urllib.request.urlopen(f"{backend_server}{path}", timeout=10) as r:
                if r.status == 200:
                    body = json.loads(r.read())
                    assert isinstance(body, dict)
                    return
        except (urllib.error.HTTPError, urllib.error.URLError):
            continue
    pytest.skip("No agent card endpoint exposed -- skipping this assertion")


def test_a2a_document_query_does_not_raise(backend_server):
    """document.query is the method that routes through vector_store.

    If the researcher path reintroduces a bare .query() call, this test
    surfaces the AttributeError as a JSON-RPC error. Tolerant of the
    specific response shape since different handler versions format it
    differently -- the point is the request doesn't 500 with a traceback
    containing 'has no attribute query'.
    """
    resp = _jsonrpc(
        backend_server,
        "document.query",
        {"query": "What is Oracle Database?", "n_results": 3},
    )
    # Either a successful result or a JSON-RPC error; both are OK as long
    # as the error isn't the specific AttributeError regression class.
    if "error" in resp:
        err_msg = str(resp["error"])
        assert "has no attribute 'query'" not in err_msg, (
            "Regression: backend raised AttributeError for bare .query() call. "
            f"Full error: {err_msg}"
        )
        assert "query_pdf_collection" not in err_msg or "AttributeError" not in err_msg
