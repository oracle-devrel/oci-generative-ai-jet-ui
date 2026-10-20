"""Recorded runs: what a run keeps of each tool's result, and the uses linked to runs."""

import logging
import json

import pytest

from golestan_code_mcp.memory import findings
from golestan_code_mcp.memory import runs as memory_runs
from golestan_code_mcp.server import graph_tools
from golestan_code_mcp.server import repository_tools
from golestan_code_mcp.server import search_tools
from golestan_code_mcp.server import wiki_tools
from golestan_code_mcp.search import feedback as search_feedback

from memory.helpers import FORBIDDEN, HIT, a_use, fields, hit, synthetic, uses_of


def test_search_run_keeps_locations_not_snippets():
    result = search_tools.SearchResults(status="ok", reason=None, results=[search_tools.SearchHit(**HIT)])
    run = memory_runs.run_of("search_code", {"query": "where is url_for defined", "repo": "flask"}, result, "c 1", 12)
    assert run["question"] == "where is url_for defined" and run["status"] == "ok" and run["reason"] is None
    assert run["result_count"] == 1 and run["repos"] == ["flask"] and run["client"] == "c 1" and run["ms"] == 12
    assert run["results"] == [{"kind": "function", "repo": "flask", "name": "url_for", "path": "src/flask/helpers.py",
                               "start_line": 188, "end_line": 246, "score": 40.0, "similarity": 0.6}]
    assert not fields(run) & FORBIDDEN


def test_symbol_run_drops_source():
    result = search_tools.SymbolResults(status="ok", reason=None, total=2, results=[search_tools.SymbolHit(
        name="url_for", kind="function", repo="flask", path="a.py", start_line=1, end_line=9, source="x" * 50,
        cut=False)])
    run = memory_runs.run_of("get_symbol", {"name": "url_for"}, result, None, 3)
    assert run["question"] == "url_for" and run["repos"] == ["flask"] and not fields(run) & FORBIDDEN


@pytest.mark.parametrize(("tool", "envelope", "hit", "row", "kept"), [
    ("find_callers", graph_tools.CallerResults, graph_tools.CallerHit,
     dict(repo="flask", kind="method", name="Flask.redirect", path="app.py", line=88, callee="url_for"),
     {"line": 88, "callee": "url_for"}),
    ("find_callees", graph_tools.CalleeResults, graph_tools.CalleeHit,
     dict(caller="url_for", line=4, repo="flask", kind="function", name="_ctx", path="g.py", start_line=1,
          end_line=3), {"caller": "url_for", "start_line": 1}),
    ("impact_of", graph_tools.ImpactResults, graph_tools.ImpactHit,
     dict(hops=2, repo="flask", kind="function", name="f", path="g.py", start_line=1, end_line=3), {"hops": 2}),
])
def test_graph_runs_keep_their_columns(tool, envelope, hit, row, kept):
    run = memory_runs.run_of(tool, {"name": "url_for"}, envelope(status="ok", reason=None, results=[hit(**row)]), None, 1)
    assert kept.items() <= run["results"][0].items() and run["repos"] == ["flask"]


def test_wiki_page_is_one_row_and_list_is_pages():
    page = wiki_tools.WikiPage(name="flask/json", repo="flask", directory="src/flask/json", language="python",
                        state="fresh", compiled_at="2026-10-12T00:00:00Z", compiler="w", stale_reason=None, symbols=10,
                        text="long page text", citations=[], truncated=False)
    run = memory_runs.run_of("read_wiki", {"page": "flask/json"}, wiki_tools.WikiResults(status="ok", reason=None, page=page),
                        None, 1)
    assert run["results"] == [{"kind": "page", "name": "flask/json", "repo": "flask", "path": "src/flask/json"}]
    listing = wiki_tools.WikiResults(status="ok", reason=None, pages=[wiki_tools.WikiPageInfo(
        name="flask/json", repo="flask", state="fresh", summary="JSON helpers")])
    run = memory_runs.run_of("read_wiki", {}, listing, None, 1)
    assert run["question"] is None and run["results"][0]["kind"] == "page" and not fields(run) & FORBIDDEN


def test_list_repositories_and_failures():
    repos = repository_tools.RepoList(database="reachable", reason=None,
                         repositories=[repository_tools.RepoInfo(name="flask", path="/x", files=1, symbols=2)])
    run = memory_runs.run_of("list_repositories", {}, repos, None, 1)
    assert (run["status"], run["question"], run["repos"]) == ("ok", None, [])
    assert run["results"] == [{"kind": "repository", "name": "flask"}]
    down = repository_tools.RepoList(database="unreachable", reason="down", repositories=[])
    assert memory_runs.run_of("list_repositories", {}, down, None, 1)["status"] == "unavailable"
    refused = search_tools.SearchResults(status="unavailable", reason="the question is empty", results=[])
    run = memory_runs.run_of("search_code", {"query": ""}, refused, None, 0)
    assert (run["status"], run["reason"], run["result_count"], run["results"]) == (
        "unavailable", "the question is empty", 0, [])
    crashed = memory_runs.run_of("get_symbol", {"name": "x"}, None, None, 5)
    assert (crashed["status"], crashed["result_count"]) == ("error", 0)


def test_repositories_come_from_results_without_a_repo_argument():
    hits = [search_tools.SearchHit(**HIT), search_tools.SearchHit(**HIT | {"repo": "gin", "rank": 2}), search_tools.SearchHit(**HIT | {"rank": 3})]
    run = memory_runs.run_of("search_code", {"query": "url_for"}, search_tools.SearchResults(status="ok", reason=None, results=hits),
                        None, 1)
    assert run["repos"] == ["flask", "gin"]


def test_store_runs_gives_each_run_its_id(ready, repo):
    name, _ = repo
    runs = [synthetic(name, "search_code", "a", []), synthetic(name, "search_code", "b", [])]
    memory_runs.store_runs(ready, runs)
    with ready.cursor() as cur:
        newest = cur.execute("select max(id) from ccctx_memory_runs").fetchone()[0]
    assert [r["id"] for r in runs] == [newest - 1, newest]


def test_a_use_queued_after_its_run_is_linked_to_it(ready, repo):
    name, _ = repo
    run = synthetic(name, "search_code", "where is spin_widget", [hit(name, "spin_widget")])
    memory_runs.record(run)
    memory_runs.record(a_use(name, "spin_widget", run))
    assert uses_of(ready, name) == [("spin_widget", "cited", run["id"])]


def test_a_use_whose_run_was_never_written_is_unlinked(ready, repo):
    name, _ = repo
    memory_runs.record(a_use(name, "spin_widget", synthetic(name, "search_code", "x", []), how="opened"))
    memory_runs.record(a_use(name, "turn_helper"))
    assert uses_of(ready, name) == [("spin_widget", "opened", None), ("turn_helper", "cited", None)]


def test_a_failing_use_is_logged_and_the_writer_goes_on(ready, repo, monkeypatch, caplog):
    name, _ = repo

    def broken(*_):
        raise RuntimeError("no table")

    write_use = search_feedback.write_use
    monkeypatch.setattr(search_feedback, "write_use", broken)
    with caplog.at_level(logging.WARNING, logger="golestan_code_mcp.memory"):
        memory_runs.record(a_use(name, "spin_widget"))
        memory_runs.flush()
    monkeypatch.setattr(search_feedback, "write_use", write_use)
    run = synthetic(name, "search_code", "after", [])
    memory_runs.record(run)
    memory_runs.flush()
    assert [json.loads(r.getMessage()) for r in caplog.records if "feedback_record_failed" in r.getMessage()] == [
        {"event": "feedback_record_failed", "reason": "no table"}]
    assert run.get("id") and uses_of(ready, name) == []


def test_runs_list_their_used_results_in_result_order(ready, repo):
    name, _ = repo
    run = synthetic(name, "search_code", "widgets", [hit(name, "spin_widget"), hit(name, "turn_helper"),
                                                     hit(name, "Widget", kind="class")])
    memory_runs.record(run)
    memory_runs.record(a_use(name, "Widget", run))
    memory_runs.record(a_use(name, "spin_widget", run, how="opened"))
    memory_runs.flush()
    [view] = [r for r in memory_runs.runs(ready, name) if r.id == run["id"]]
    assert view.used == ["spin_widget", "Widget"]
    assert all(r.used == [] for r in memory_runs.runs(ready, name) if r.id != run["id"])


def test_mark_used_makes_no_fact():
    assert "mark_used" in findings.NO_FACTS
