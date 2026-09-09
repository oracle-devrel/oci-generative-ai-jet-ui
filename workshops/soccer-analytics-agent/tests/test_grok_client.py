import pytest
import respx
from httpx import Response

from soccer_agent.agent.grok_client import _parse_tool_calls, chat


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv("OCI_GENAI_ENDPOINT",
                       "https://inference.generativeai.us-phoenix-1.oci.oraclecloud.com")
    monkeypatch.setenv("OCI_GENAI_API_KEY", "sk-test")
    monkeypatch.setenv("OCI_COMPARTMENT_ID", "ocid1.compartment.oc1..x")
    monkeypatch.setenv("OCI_GENAI_MODEL_ID", "xai.grok-4")


@respx.mock
def test_chat_returns_text():
    respx.post(
        "https://inference.generativeai.us-phoenix-1.oci.oraclecloud.com/20231130/actions/chat"
    ).mock(return_value=Response(200, json={
        "chatResponse": {"choices": [{
            "message": {"role": "ASSISTANT",
                        "content": [{"type": "TEXT", "text": "pong"}]},
        }]},
    }))
    r = chat([{"role": "user", "content": "ping"}], tool_schemas=[])
    assert r.text == "pong"
    assert r.tool_calls == []


@respx.mock
def test_chat_parses_tool_call():
    respx.post(
        "https://inference.generativeai.us-phoenix-1.oci.oraclecloud.com/20231130/actions/chat"
    ).mock(return_value=Response(200, json={
        "chatResponse": {"choices": [{
            "message": {
                "role": "ASSISTANT",
                "content": [],
                "toolCalls": [{
                    "id": "c1",
                    "type": "FUNCTION",
                    "function": {"name": "sql_query",
                                 "arguments": "{\"sql\":\"SELECT 1 FROM DUAL\"}"},
                }],
            },
        }]},
    }))
    r = chat([{"role": "user", "content": "test"}],
             tool_schemas=[{"name": "sql_query", "description": "", "parameters": {}}])
    assert r.tool_calls == [{
        "id": "c1", "name": "sql_query",
        "arguments": "{\"sql\":\"SELECT 1 FROM DUAL\"}",
    }]


@respx.mock
def test_chat_retries_on_500():
    route = respx.post(
        "https://inference.generativeai.us-phoenix-1.oci.oraclecloud.com/20231130/actions/chat"
    ).mock(side_effect=[
        Response(500, json={"code": "500", "message": "boom"}),
        Response(200, json={"chatResponse": {"choices": [{
            "message": {"role": "ASSISTANT",
                        "content": [{"type": "TEXT", "text": "ok"}]},
        }]}}),
    ])
    r = chat([{"role": "user", "content": "x"}])
    assert r.text == "ok"
    assert route.call_count == 2


@respx.mock
def test_chat_4xx_raises():
    respx.post(
        "https://inference.generativeai.us-phoenix-1.oci.oraclecloud.com/20231130/actions/chat"
    ).mock(return_value=Response(401, json={"code": "401", "message": "bad key"}))
    with pytest.raises(RuntimeError, match="401"):
        chat([{"role": "user", "content": "x"}])


# ---------------------------------------------------------------------------
# _parse_tool_calls unit tests — no HTTP needed
# ---------------------------------------------------------------------------

def test_parse_tool_calls_single_line():
    """Standard single-line tool call emitted by Grok."""
    text = 'Sure, let me look that up.\n{"tool": "get_elo", "args": {"team": "Spain"}}\n'
    result = _parse_tool_calls(text)
    assert len(result) == 1
    assert result[0]["name"] == "get_elo"
    import json
    assert json.loads(result[0]["arguments"]) == {"team": "Spain"}


def test_parse_tool_calls_multiline_indented():
    """Pretty-printed / indented tool call that the single-line regex misses."""
    text = (
        "I will call the tool now.\n"
        "{\n"
        '  "tool": "predict_match",\n'
        '  "args": {"home_team": "Spain", "away_team": "Brazil", "neutral": true}\n'
        "}\n"
    )
    result = _parse_tool_calls(text)
    assert len(result) == 1
    assert result[0]["name"] == "predict_match"
    import json
    args = json.loads(result[0]["arguments"])
    assert args["home_team"] == "Spain"
    assert args["away_team"] == "Brazil"


def test_parse_tool_calls_nested_args():
    """Tool call whose args dict contains a nested object."""
    import json
    text = '{"tool": "sql_query", "args": {"sql": "SELECT * FROM MATCH_RESULTS FETCH FIRST 5 ROWS ONLY"}}'
    result = _parse_tool_calls(text)
    assert len(result) == 1
    assert result[0]["name"] == "sql_query"
    assert "SELECT" in json.loads(result[0]["arguments"])["sql"]


def test_parse_tool_calls_no_match():
    """Plain prose with no tool call returns an empty list."""
    text = "Spain has a strong Elo rating of around 1950 points."
    result = _parse_tool_calls(text)
    assert result == []


def test_parse_tool_calls_malformed_json_ignored():
    """A line that looks like a tool call but is broken JSON is skipped."""
    text = '{"tool": "get_elo", "args": {broken}'
    result = _parse_tool_calls(text)
    assert result == []


def test_parse_tool_calls_empty_args():
    """Tool call with no args field defaults to empty dict."""
    import json
    text = '{"tool": "recall"}'
    result = _parse_tool_calls(text)
    assert len(result) == 1
    assert result[0]["name"] == "recall"
    assert json.loads(result[0]["arguments"]) == {}
