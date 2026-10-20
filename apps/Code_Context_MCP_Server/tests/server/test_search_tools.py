"""search_code and get_symbol: the same results as the core, refusals, pages, feedback and languages."""

import asyncio
import subprocess
import uuid
from pathlib import Path

import pytest

from golestan_code_mcp import db, registry
from golestan_code_mcp.indexing import ingest as indexing_ingest
from golestan_code_mcp.search import query
from golestan_code_mcp.config import load

from server.helpers import _session, call, definitions, ready


def test_search_code_hits_can_be_pages():
    hit = asyncio.run(_session(lambda c: c.list_tools())).tools[0].outputSchema["$defs"]["SearchHit"]["properties"]
    for line in ("start_line", "end_line"):
        assert {t.get("type") for t in hit[line]["anyOf"]} == {"integer", "null"}
    assert {t.get("type") for t in hit["state"]["anyOf"]} == {"string", "null"}


@pytest.mark.parametrize("arguments", [
    {"query": "how are requests routed", "repo": "flask"},
    {"query": "url_for"},
    {"query": "middleware chain", "repo": "gin", "language": "go", "limit": 3},
    {"query": "url_for", "language": "python", "limit": 50},
])
def test_search_code_matches_core(arguments):
    conn = ready()
    repo = arguments.get("repo")
    try:
        with conn:
            expected = [vars(r) for r in query.search(conn, arguments["query"], [repo] if repo else None,
                                                         language=arguments.get("language"),
                                                         limit=arguments.get("limit", 10))]
    except Exception as e:  # repositories not registered in this database
        pytest.skip(f"sample repositories not indexed: {e}")
    result = call("search_code", **arguments)
    assert result == {"status": "ok", "reason": None, "results": expected}
    assert all(h["repo"] and h["path"] for h in result["results"])
    assert all(h["start_line"] <= h["end_line"] for h in result["results"] if h["kind"] != "page")
    assert all(h["start_line"] is None and h["state"] for h in result["results"] if h["kind"] == "page")


@pytest.mark.parametrize(("arguments", "reason"), [
    ({"query": "  "}, "the question is empty"),
    ({"query": "routing", "limit": 0}, "limit must be between 1 and 50"),
    ({"query": "routing", "limit": 51}, "limit must be between 1 and 50"),
    ({"query": "routing", "language": "cobol"},
     f"unknown language 'cobol'; valid languages: {', '.join(query.LANGUAGES)}"),
])
def test_search_code_input_refused_before_connecting(monkeypatch, arguments, reason):
    monkeypatch.setenv("DB_PORT", "1")
    assert call("search_code", **arguments) == {"status": "unavailable", "reason": reason, "results": []}


def test_search_code_unknown_repository_is_a_result():
    try:
        db.connect(load()).close()
    except Exception:
        pytest.skip("database unreachable")
    assert call("search_code", query="routing", repo="t-missing") == {
        "status": "unavailable", "reason": "no repository named 't-missing'", "results": []}


@pytest.mark.parametrize("arguments", [
    {"name": "Flask.dispatch_request"},
    {"name": "url_for", "repo": "flask"},
    {"name": "get"},  # many definitions: capped at 5
])
def test_get_symbol_matches_core(arguments):
    expected, total = definitions(arguments["name"], arguments.get("repo"))
    result = call("get_symbol", **arguments)
    assert result == {"status": "ok", "reason": None, "results": expected, "total": total,
                      "truncated": total > len(expected)}
    assert len(result["results"]) <= 5 and all(h["source"] for h in result["results"])


def test_get_symbol_refusals_are_results(monkeypatch):
    empty = {"results": [], "total": 0, "truncated": False}
    try:
        db.connect(load()).close()
    except Exception:
        pytest.skip("database unreachable")
    assert call("get_symbol", name="t_no_such_symbol_anywhere") == {
        "status": "unavailable", "reason": "no symbol named 't_no_such_symbol_anywhere'", **empty}
    assert call("get_symbol", name="url_for", repo="t-missing") == {
        "status": "unavailable", "reason": "no repository named 't-missing'", **empty}
    monkeypatch.setenv("DB_PORT", "1")
    assert call("get_symbol", name="  ") == {"status": "unavailable", "reason": "the name is empty", **empty}


def test_search_hits_carry_relevance_and_feedback(fresh_session):
    on = call("search_code", query="post entry for the demo ledger", repo=fresh_session)["results"]
    off = call("search_code", query="post entry for the demo ledger", repo=fresh_session, feedback=False)["results"]
    assert on and all(0 <= h["feedback"] <= 0.2 for h in on)
    assert all(h["score"] == pytest.approx(h["relevance"] * (1 + h["feedback"])) for h in on)
    assert all(h["feedback"] == 0 for h in off)


def test_search_with_feedback_off_matches_the_core(fresh_session):
    with db.connect(load()) as conn:
        expected = [vars(r) for r in query.search(conn, "post entry", [fresh_session], feedback=False)]
    assert call("search_code", query="post entry", repo=fresh_session, feedback=False)["results"] == expected


# --- language coverage (specs/012-language-coverage contracts/tools.md) ------------------------------------------


def test_an_unknown_language_lists_the_new_ones(monkeypatch):
    monkeypatch.setenv("DB_PORT", "1")
    reason = call("search_code", query="x", language="cobol")["reason"]
    assert reason == f"unknown language 'cobol'; valid languages: {', '.join(query.LANGUAGES)}"
    assert {"csharp", "typescript", "tsx", "c", "cpp", "java", "kotlin", "rust", "php", "ruby", "swift"} <= set(
        reason.split(": ", 1)[1].split(", "))


def test_search_code_finds_csharp_definitions_as_the_core_does(tmp_path):
    import shutil

    conn = ready()
    with conn:
        root = tmp_path / "repo"
        shutil.copytree(Path(__file__).resolve().parents[1] / "fixtures" / "languages" / "csharp", root)
        for args in (["init", "-q"], ["add", "-A"], ["commit", "-q", "-m", "init"]):
            subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", *args], cwd=root, check=True,
                           capture_output=True)
        name = f"t-{uuid.uuid4().hex[:8]}"
        registry.add_repo(conn, str(root), name)
        try:
            indexing_ingest.ingest(conn, name)
            expected = [vars(r) for r in query.search(conn, "start the browser", [name], language="csharp")]
            result = call("search_code", query="start the browser", repo=name, language="csharp")
            assert result == {"status": "ok", "reason": None, "results": expected}
            assert expected and {h["language"] for h in expected} == {"csharp"}
            assert "DriverFixture.Start" in {h["name"] for h in expected}
        finally:
            with conn.cursor() as cur:
                cur.execute("delete from ccctx_repos where name = :n", n=name)
            conn.commit()
