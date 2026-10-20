"""What every tool shares: the listing and instructions, refused arguments, outages, logs and recorded runs."""

import json
import logging
import time

import pytest

from golestan_code_mcp import db
from golestan_code_mcp.server import app
from golestan_code_mcp.server import search_tools
from golestan_code_mcp.config import load
from golestan_code_mcp.memory import runs

from server.helpers import (CALLS, TOOLS, UNREACHABLE, as_client, call, contract, instructions, listed, raw_call,
    runs_since)


def test_lists_the_nine_tools_as_the_contract_describes_them():
    tools = listed()
    assert list(tools) == TOOLS
    descriptions, params = contract()
    for name, tool in tools.items():
        assert tool.description == descriptions[name], name
        assert tool.annotations.readOnlyHint is (name != "mark_used")
        assert tool.inputSchema.get("additionalProperties") is False
        for param, spec in tool.inputSchema.get("properties", {}).items():
            assert spec["description"] == params[(name, param)], (name, param)
    shape = {n: (list(t.inputSchema.get("properties", {})), t.inputSchema.get("required", [])) for n, t in tools.items()}
    assert shape == {
        "search_code": (["query", "repo", "language", "limit", "feedback"], ["query"]),
        "get_symbol": (["name", "repo"], ["name"]),
        "find_callers": (["name", "repo"], ["name"]),
        "find_callees": (["name", "repo"], ["name"]),
        "impact_of": (["name", "depth", "repo"], ["name"]),
        "read_wiki": (["page", "repo"], []),
        "list_repositories": ([], []),
        "recall": (["repo", "topic", "limit"], []),
        "mark_used": (["repo", "path", "name"], ["repo", "path", "name"]),
    }
    marks = tools["mark_used"].annotations
    assert (marks.idempotentHint, marks.destructiveHint) == (True, False)
    assert tools["search_code"].inputSchema["properties"]["feedback"]["default"] is True
    assert tools["recall"].inputSchema["properties"]["limit"]["default"] == 20
    assert tools["search_code"].inputSchema["properties"]["limit"]["default"] == 10
    assert tools["impact_of"].inputSchema["properties"]["depth"]["default"] == 3


@pytest.mark.parametrize(("tool", "arguments", "argument"), [
    ("find_callers", {"name": "url_for", "repos": ["flask"]}, "repos"),
    ("search_code", {"query": "routing", "question": "routing"}, "question"),
    ("read_wiki", {"name": "flask/json"}, "name"),
])
def test_unknown_arguments_are_refused(monkeypatch, tool, arguments, argument):
    monkeypatch.setenv("DB_PORT", "1")
    result = raw_call(tool, **arguments)
    assert result.isError and argument in result.content[0].text


def test_missing_password_named(monkeypatch):
    monkeypatch.setenv("DB_PASSWORD", "")
    result = call("search_code", query="routing")
    assert result["status"] == "unavailable" and "DB_PASSWORD" in result["reason"]


@pytest.mark.parametrize(("tool", "arguments"), UNREACHABLE)
def test_unreachable_is_a_result(monkeypatch, tool, arguments):
    monkeypatch.setenv("DB_PORT", "1")
    monkeypatch.setenv("DB_PASSWORD", "Not-A-Real-Pw-42")
    started = time.monotonic()
    result = call(tool, **arguments)
    assert time.monotonic() - started < 10
    assert result["status"] == "unavailable" and result["reason"] and result.get("results", result.get("pages")) == []
    assert "Not-A-Real-Pw-42" not in result["reason"]


def test_next_call_after_an_outage_succeeds(monkeypatch):
    try:
        db.connect(load()).close()
    except Exception:
        pytest.skip("database unreachable")
    monkeypatch.setenv("DB_PORT", "1")
    assert call("list_repositories")["database"] == "unreachable"
    monkeypatch.undo()  # the database is back; same server, no restart
    assert call("list_repositories")["database"] == "reachable"


def test_each_tool_call_is_logged(monkeypatch, caplog):
    monkeypatch.setenv("DB_PORT", "1")
    caplog.set_level(logging.INFO, logger="golestan_code_mcp.server")
    call("list_repositories")
    call("search_code", query="secret_marker_question")
    call("get_symbol", name="secret_marker_name")
    call("find_callers", name="secret_marker_name")
    call("impact_of", name="secret_marker_name")
    call("read_wiki", page="secret_marker_name")
    records = [json.loads(r.getMessage()) for r in caplog.records if r.name == "golestan_code_mcp.server"]
    assert [(r["event"], r["tool"], r["status"], r["results"]) for r in records] == [
        ("tool", "list_repositories", "unreachable", 0),
        ("tool", "search_code", "unavailable", 0),
        ("tool", "get_symbol", "unavailable", 0),
        ("tool", "find_callers", "unavailable", 0),
        ("tool", "impact_of", "unavailable", 0),
        ("tool", "read_wiki", "unavailable", 0),
    ]
    assert all(isinstance(r["ms"], int) for r in records)
    assert "secret_marker_question" not in caplog.text and "secret_marker_name" not in caplog.text  # never arguments


@pytest.mark.parametrize(("tool", "arguments"), CALLS)
def test_every_tool_call_is_one_run(recorded, tool, arguments):
    conn, before = recorded
    result = as_client(tool, **arguments)
    assert not result.isError
    rows = runs_since(conn, before)
    assert len(rows) == 1
    name, args, question, client, status, reason, count = rows[0]
    assert (name, client) == (tool, "test-client 9.9")
    assert arguments.items() <= args.items() and None not in args.values()  # the effective call, defaults included
    assert question == next((arguments[k] for k in ("query", "name", "page", "topic") if k in arguments), None)
    envelope = result.structuredContent
    assert status == envelope.get("status", "ok") and reason == envelope.get("reason")
    assert count == len(next((v for k, v in envelope.items() if k in ("results", "pages", "repositories", "facts")), []))


@pytest.mark.parametrize(("tool", "arguments", "reason"), [
    ("search_code", {"query": ""}, "the question is empty"),
    ("get_symbol", {"name": "url_for", "repo": "t-nowhere"}, "no repository named 't-nowhere'"),
])
def test_refused_calls_are_recorded_unavailable(recorded, tool, arguments, reason):
    conn, before = recorded
    as_client(tool, **arguments)
    [(name, _, _, _, status, why, count)] = runs_since(conn, before)
    assert (name, status, count) == (tool, "unavailable", 0) and reason in why


def test_recording_failure_leaves_the_answer_alone(recorded, monkeypatch, caplog):
    conn, before = recorded
    expected = as_client("list_repositories").structuredContent
    runs.flush()

    def broken(*_):
        raise RuntimeError("store down")

    monkeypatch.setattr(runs, "store_runs", broken)
    with caplog.at_level(logging.WARNING, logger="golestan_code_mcp.memory"):
        assert as_client("list_repositories").structuredContent == expected
        runs.flush()
    failures = [json.loads(r.getMessage()) for r in caplog.records if "memory_record_failed" in r.getMessage()]
    assert failures == [{"event": "memory_record_failed", "tool": "list_repositories", "reason": "store down"}]


def test_tool_log_record_is_unchanged(recorded, caplog):
    with caplog.at_level(logging.INFO, logger="golestan_code_mcp.server"):
        as_client("list_repositories")
    records = [json.loads(r.getMessage()) for r in caplog.records if r.name == "golestan_code_mcp.server"]
    assert records and set(records[-1]) == {"event", "tool", "ms", "status", "results"}


# --- recall (specs/010-agent-memory contracts/tools.md) --------------------------------------------------------


def test_server_instructions_match_the_contract():
    assert app.mcp.instructions == instructions()


def test_recording_adds_no_visible_delay(recorded, monkeypatch):
    """SC-008: the median of 20 calls with recording is within 5% (plus 10 ms of timer noise) of the median without."""
    import statistics

    def median_ms():
        times = []
        for _ in range(20):
            started = time.perf_counter()
            search_tools.get_symbol(name="url_for", repo="flask")
            times.append(time.perf_counter() - started)
        return statistics.median(times)

    median_ms()  # warm up the connection path
    with_recording = median_ms()
    runs.flush()
    monkeypatch.setattr(runs, "record", lambda run: None)
    without = median_ms()
    assert with_recording <= without * 1.05 + 0.010
