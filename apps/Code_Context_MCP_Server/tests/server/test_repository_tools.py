"""list_repositories: the registry's repositories, and an outage as a result."""

import pytest

from golestan_code_mcp import db, registry, schema
from golestan_code_mcp.config import load

from server.helpers import call


def test_list_repositories_matches_registry():
    try:
        conn = db.connect(load())
    except Exception:
        pytest.skip("database unreachable")
    with conn:
        schema.migrate(conn)
        expected = [vars(r) for r in registry.list_repos(conn)]
    assert call("list_repositories") == {"database": "reachable", "reason": None, "repositories": expected}


def test_list_repositories_unreachable_is_a_result(monkeypatch):
    monkeypatch.setenv("DB_PORT", "1")
    monkeypatch.setenv("DB_PASSWORD", "Not-A-Real-Pw-42")
    result = call("list_repositories")
    assert result["database"] == "unreachable" and result["reason"] and result["repositories"] == []
    assert "Not-A-Real-Pw-42" not in result["reason"]
