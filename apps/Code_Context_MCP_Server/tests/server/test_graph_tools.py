"""find_callers, find_callees and impact_of: the same results as the core, caps and refusals."""

import pytest

from golestan_code_mcp import db
from golestan_code_mcp.server import app
from golestan_code_mcp.config import load

from server.helpers import GRAPH_CALLS, call, core


@pytest.mark.parametrize(("tool", "arguments"), GRAPH_CALLS)
def test_graph_tools_match_core(tool, arguments):
    expected = core(tool, arguments)
    result = call(tool, **arguments)
    assert result == {"status": "ok", "reason": None, "results": expected[:200], "truncated": len(expected) > 200}
    assert all(h["repo"] and h["path"] for h in result["results"])


def test_graph_results_are_capped(monkeypatch):
    expected = core("find_callers", {"name": "url_for", "repo": "flask"})
    if len(expected) < 2:
        pytest.skip("flask graph not built")
    monkeypatch.setattr(app, "LIMIT", 1)
    result = call("find_callers", name="url_for", repo="flask")
    assert result["results"] == expected[:1] and result["truncated"] is True


@pytest.mark.parametrize(("tool", "arguments", "reason"), [
    ("find_callers", {"name": "  "}, "the name is empty"),
    ("find_callees", {"name": ""}, "the name is empty"),
    ("impact_of", {"name": "url_for", "depth": 0}, "depth must be between 1 and 5"),
    ("impact_of", {"name": "url_for", "depth": 6}, "depth must be between 1 and 5"),
])
def test_graph_input_refused_before_connecting(monkeypatch, tool, arguments, reason):
    monkeypatch.setenv("DB_PORT", "1")
    assert call(tool, **arguments) == {"status": "unavailable", "reason": reason, "results": [], "truncated": False}


@pytest.mark.parametrize(("tool", "arguments", "reason"), [
    ("find_callees", {"name": "url_for", "repo": "t-missing"}, "no repository named 't-missing'"),
    ("find_callers", {"name": "t_no_such_symbol_anywhere"}, "no symbol named 't_no_such_symbol_anywhere'"),
])
def test_graph_refusals_are_results(tool, arguments, reason):
    try:
        db.connect(load()).close()
    except Exception:
        pytest.skip("database unreachable")
    assert call(tool, **arguments) == {"status": "unavailable", "reason": reason, "results": [], "truncated": False}
