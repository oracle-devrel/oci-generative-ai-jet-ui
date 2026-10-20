"""recall and mark_used: recall as the core gives it, and uses linked to the searches that returned them."""

import json
import logging

import pytest

from golestan_code_mcp.memory import recall
from golestan_code_mcp.memory import runs
from golestan_code_mcp.memory import store
from golestan_code_mcp.search import feedback as search_feedback

from server.helpers import as_client, call, newest_run, ready, search_hit, uses


@pytest.mark.parametrize(("arguments", "reason"), [
    ({"limit": 0}, "limit must be between 1 and 50"),
    ({"limit": 51}, "limit must be between 1 and 50"),
    ({"topic": "  "}, "the topic is empty"),
])
def test_recall_refuses_bad_input_before_connecting(monkeypatch, arguments, reason):
    monkeypatch.setenv("DB_PORT", "1")
    out = call("recall", **arguments)
    assert out == {"status": "unavailable", "reason": reason, "facts": [], "runs": [], "total": 0, "truncated": False}


def test_recall_database_down(monkeypatch):
    monkeypatch.setenv("DB_PORT", "1")
    out = call("recall", repo="flask")
    assert out["status"] == "unavailable" and out["reason"] and out["facts"] == [] and out["runs"] == []


def test_recall_unknown_repository():
    ready().close()
    out = call("recall", repo="t-nowhere")
    assert out["status"] == "unavailable" and out["reason"] == "no repository named 't-nowhere'"


def test_recall_matches_core_and_shape(monkeypatch):
    conn = ready()
    calls = []

    class Spy:
        def generate(self, *a, **k):
            calls.append(a)

    monkeypatch.setattr(store, "model", lambda env=None: (Spy(), "llm:spy"))
    with conn:
        expected = recall.recall(conn, "flask", None, 20)
    out = call("recall", repo="flask")
    assert out["status"] == "ok" and out["total"] == expected.total
    assert out["truncated"] == (expected.total > len(out["facts"]))
    assert [f["id"] for f in out["facts"]] == [f.id for f in expected.facts]
    assert [r["id"] for r in out["runs"]] == [r.id for r in expected.runs]
    assert len(out["runs"]) <= 10 and all(r["tool"] != "recall" for r in out["runs"])
    for f in out["facts"]:
        assert set(f) == {"id", "repo", "subject", "kind", "state", "stale_reason", "confidence", "distiller", "text",
                          "questions", "runs", "updated_at", "sources"}
        assert len(f["questions"]) <= 5 and len(f["runs"]) <= 20 and f["sources"][0]["role"] == "subject"
    for r in out["runs"]:
        assert set(r) == {"id", "at", "tool", "question", "client", "status", "result_count", "top"}
    assert calls == []  # recall never calls the model


def test_mark_used_after_a_search_is_linked(recorded, fresh_session):
    conn, _ = recorded
    hit = search_hit(fresh_session, "post3")
    out = as_client("mark_used", repo=fresh_session, path=hit["path"], name="post3").structuredContent
    assert out == {"status": "ok", "reason": None, "repo": fresh_session, "path": hit["path"], "name": "post3",
                   "kind": "function", "linked": True}
    assert uses(conn, fresh_session) == [("post3", hit["path"], "function", "cited", newest_run(conn, "search_code"),
                                          "test-client 9.9")]


def test_mark_used_without_a_search_is_unlinked(recorded, fresh_session):
    conn, _ = recorded
    out = as_client("mark_used", repo=fresh_session, path="src/pkg/core.py", name="post1").structuredContent
    assert out["status"] == "ok" and out["linked"] is False
    assert [(n, how, run) for n, _, _, how, run, _ in uses(conn, fresh_session)] == [("post1", "cited", None)]


@pytest.mark.parametrize("arguments", [
    {"path": "src/pkg/core.py", "name": "no_such_post"},
    {"path": "src/pkg/other.py", "name": "post1"},
])
def test_mark_used_on_nothing_records_nothing(recorded, fresh_session, arguments):
    conn, _ = recorded
    out = as_client("mark_used", repo=fresh_session, **arguments).structuredContent
    assert out["status"] == "unavailable" and out["reason"].startswith("not found: ") and out["kind"] is None
    assert out["linked"] is False and uses(conn, fresh_session) == []


def test_mark_used_unknown_repository(recorded):
    out = as_client("mark_used", repo="t-nowhere", path="a.py", name="f").structuredContent
    assert out["status"] == "unavailable" and out["reason"] == "no repository named 't-nowhere'"


def test_reading_a_returned_hit_is_an_opened_use(recorded, fresh_session):
    conn, _ = recorded
    out = as_client("search_code", query="post entry for the demo ledger", repo=fresh_session, limit=20)
    returned = {h["name"] for h in out.structuredContent["results"]}
    run = newest_run(conn, "search_code")
    assert as_client("get_symbol", name="post5", repo=fresh_session).structuredContent["status"] == "ok"
    assert as_client("read_wiki", page="pkg", repo=fresh_session).structuredContent["status"] == "ok"
    expected = [("post5", "src/pkg/core.py", "function", "opened", run, "test-client 9.9")]
    if "pkg" in returned:  # the page is an opened use only when the search returned it
        expected.append(("pkg", "src/pkg", "page", "opened", run, "test-client 9.9"))
    assert uses(conn, fresh_session) == expected


def test_reading_without_a_search_is_not_a_use(recorded, fresh_session):
    conn, _ = recorded
    as_client("get_symbol", name="post5", repo=fresh_session)
    as_client("read_wiki", page="pkg", repo=fresh_session)
    assert uses(conn, fresh_session) == []


def test_opened_then_cited_is_one_cited_use(recorded, fresh_session):
    conn, _ = recorded
    hit = search_hit(fresh_session, "post7")
    as_client("get_symbol", name="post7", repo=fresh_session)
    as_client("mark_used", repo=fresh_session, path=hit["path"], name="post7")
    as_client("mark_used", repo=fresh_session, path=hit["path"], name="post7")
    assert [(n, how) for n, _, _, how, _, _ in uses(conn, fresh_session)] == [("post7", "cited")]


def test_a_use_recording_failure_leaves_the_answer_alone(recorded, fresh_session, monkeypatch, caplog):
    conn, _ = recorded
    expected = as_client("mark_used", repo=fresh_session, path="src/pkg/core.py", name="post2").structuredContent
    runs.flush()

    def broken(*_):
        raise RuntimeError("feedback down")

    monkeypatch.setattr(search_feedback, "write_use", broken)
    with caplog.at_level(logging.WARNING, logger="golestan_code_mcp.memory"):
        out = as_client("mark_used", repo=fresh_session, path="src/pkg/core.py", name="post4").structuredContent
        runs.flush()
    assert out == expected | {"name": "post4"}
    failures = [json.loads(r.getMessage()) for r in caplog.records if "feedback_record_failed" in r.getMessage()]
    assert failures == [{"event": "feedback_record_failed", "reason": "feedback down"}]
    assert [n for n, *_ in uses(conn, fresh_session)] == ["post2"]
