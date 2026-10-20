"""Retrieval quality: the identifier and routing checks, the gold set, and recall with and without feedback."""

import re
import json
from pathlib import Path

import pytest

from golestan_code_mcp import db, registry
from golestan_code_mcp.search import model
from golestan_code_mcp.search import query
from golestan_code_mcp.config import load
from golestan_code_mcp.search import evaluation
from golestan_code_mcp.search import feedback as search_feedback

pytestmark = pytest.mark.needs_model  # the shared `conn` then requires the embedding model

EVAL_VERSION = 1

# SC-002: identifier -> its definitions (repo, path, symbol name); any one at rank 1 is a hit
IDENTIFIERS = {
    "url_for": {("flask", "src/flask/app.py", "Flask.url_for"), ("flask", "src/flask/helpers.py", "url_for")},
    "make_response": {("flask", "src/flask/app.py", "Flask.make_response"),
                      ("flask", "src/flask/helpers.py", "make_response")},
    "render_template": {("flask", "src/flask/templating.py", "render_template")},
    "jsonify": {("flask", "src/flask/json/__init__.py", "jsonify")},
    "send_file": {("flask", "src/flask/helpers.py", "send_file")},
    "full_dispatch_request": {("flask", "src/flask/app.py", "Flask.full_dispatch_request")},
    "handleHTTPRequest": {("gin", "gin.go", "Engine.handleHTTPRequest")},
    "addRoute": {("gin", "gin.go", "Engine.addRoute"), ("gin", "tree.go", "node.addRoute")},
    "getValue": {("gin", "tree.go", "node.getValue")},
    "Next": {("gin", "context.go", "Context.Next")},
}

# SC-003: routing or dispatch code, per repository
ROUTING_QUESTION = "how are incoming requests routed to handlers"

ROUTING = {
    "flask": {"src/flask/app.py", "src/flask/sansio/app.py", "src/flask/sansio/scaffold.py", "src/flask/views.py"},
    "gin": {"gin.go", "routergroup.go", "tree.go"},
}


@pytest.fixture(scope="module")
def conn():
    try:
        c = db.connect(load())
        model.require_model(c)
    except Exception:
        pytest.skip("database unreachable or hybrid index not built")
    indexed = {r.name for r in registry.list_repos(c) if r.symbols}
    if not {"flask", "gin"} <= indexed:
        c.close()
        pytest.skip("flask and gin are not both ingested")
    yield c
    c.close()


def where(results):
    return [(r.repo, r.path, r.name) for r in results]


def test_url_for_definitions_first(conn):  # SC-001
    found = where(query.search(conn, "url_for"))
    assert set(found[:2]) == IDENTIFIERS["url_for"]


def test_identifier_definitions_at_rank_one(conn):  # SC-002
    top = {q: where(query.search(conn, q))[:5] for q in IDENTIFIERS}
    top1 = [q for q, hits in top.items() if hits and hits[0] in IDENTIFIERS[q]]
    top5 = [q for q, hits in top.items() if IDENTIFIERS[q] & set(hits)]
    print(f"eval v{EVAL_VERSION}: top-1 {len(top1)}/{len(top)}, top-5 {len(top5)}/{len(top)}")
    assert len(top1) >= 9, f"rank-1 misses: {sorted(set(top) - set(top1))}"


def test_routing_question_finds_both_repositories(conn):  # SC-003
    found = where(query.search(conn, ROUTING_QUESTION))
    assert {repo for repo, path, _ in found if path in ROUTING.get(repo, ())} == set(ROUTING)


def test_repository_scope(conn):  # SC-004
    assert {r.repo for r in query.search(conn, "middleware chain", ["gin"])} == {"gin"}


def test_out_of_domain_question(conn):  # SC-005
    assert len(query.search(conn, "recipe for sourdough bread")) <= 3


GOLD = Path(__file__).resolve().parents[2] / "gold.json"

BASELINE_HITS = 18  # recall@10 hits without feedback for gold.json version 1, measured 2026-10-13 (T030)


def gold_file(tmp_path, text):
    path = tmp_path / "gold.json"
    path.write_text(text if isinstance(text, str) else json.dumps(text), encoding="utf-8")
    return path


QUESTION = {"question": "how are routes matched?", "repo": "flask", "paths": ["src/flask/app.py"]}


@pytest.mark.parametrize(("content", "message"), [
    ("{not json", "gold file is not valid JSON: "),
    ({"questions": [QUESTION]}, "gold file: no version"),
    ({"version": 1}, "gold file: no questions"),
    ({"version": 1, "questions": []}, "gold file: no questions"),
    ({"version": 1, "questions": [QUESTION, QUESTION | {"question": " "}]}, "gold file: question 2 is empty"),
    ({"version": 1, "questions": [QUESTION | {"paths": []}]}, "gold file: question 1 has no paths"),
    ({"version": 1, "questions": [QUESTION | {"repo": "t-nowhere"}]},
     "no repository named 't-nowhere' (gold question 1)"),
])
def test_bad_gold_files_are_refused(conn, tmp_path, content, message):
    with pytest.raises(ValueError, match="^" + re.escape(message)):
        evaluation.load_gold(gold_file(tmp_path, content), conn)


def test_a_missing_gold_file(conn, tmp_path):
    with pytest.raises(ValueError, match="^gold file not found: "):
        evaluation.load_gold(tmp_path / "none.json", conn)


def test_expected_paths_match_files_and_directories():
    assert evaluation.matches("src/flask/app.py", ["src/flask/app.py"])
    assert evaluation.matches("src/flask/json/provider.py", ["src/flask/json"])
    assert not evaluation.matches("src/flask/json_extra.py", ["src/flask/json"])
    assert not evaluation.matches("src/flask/app.py", ["src/flask/sansio/app.py"])


def counts(conn):
    with conn.cursor() as cur:
        return [cur.execute(f"select count(*) from {t}").fetchone()[0] for t in ("ccctx_memory_runs", "ccctx_feedback")]


@pytest.fixture(scope="module")
def gold(conn):
    return evaluation.load_gold(GOLD, conn)


@pytest.fixture(scope="module")
def baseline(conn, gold):
    return evaluation.evaluate(conn, gold, with_feedback=False)


def test_the_gold_set_has_twenty_questions_in_plain_words(gold):
    assert len(gold) == 20 and all(" " in q["question"] for q in gold)


def test_evaluation_records_nothing_and_holds_the_floor(conn, gold, baseline):
    before = counts(conn)
    again = evaluation.evaluate(conn, gold, with_feedback=True)
    assert counts(conn) == before and again.questions == baseline.questions == 20
    assert len(baseline.missed) == 20 - baseline.hits
    print(f"gold v1: recall@10 {baseline.recall:.2f} ({baseline.hits}/20)")
    assert BASELINE_HITS is not None and baseline.hits >= BASELINE_HITS


@pytest.fixture
def added(conn):
    """Uses this test adds to the real repositories, removed afterwards; never anyone else's."""
    with conn.cursor() as cur:
        before = cur.execute("select nvl(max(id), 0) from ccctx_feedback").fetchone()[0]
    yield
    with conn.cursor() as cur:
        cur.execute("delete from ccctx_feedback where id > :b", b=before)
    conn.commit()


def test_feedback_on_expected_results_holds_or_improves_recall(conn, gold, baseline, added):  # SC-002
    marked = 0
    for q in gold:
        hit = next((h for h in query.search(conn, q["question"], [q["repo"]], limit=50, feedback=False)
                    if h.kind not in ("page", "fact") and evaluation.matches(h.path, q["paths"])), None)
        if hit and marked < 5:
            search_feedback.add(conn, hit.repo, hit.name, hit.path, count=3)
            marked += 1
    assert marked == 5
    assert evaluation.evaluate(conn, gold, with_feedback=True).hits >= baseline.hits
    assert evaluation.evaluate(conn, gold, with_feedback=False) == baseline


def test_a_hammered_symbol_never_takes_over(conn, gold, added):  # SC-003, SC-006
    search_feedback.add(conn, "flask", "url_for", "src/flask/helpers.py", count=1000)
    for q in gold:
        without = query.search(conn, q["question"], [q["repo"]], feedback=False)
        with_ = query.search(conn, q["question"], [q["repo"]])
        if any(h.name == "url_for" for h in with_) and not any(h.name == "url_for" for h in without):
            [entered] = [h for h in with_ if h.name == "url_for"]
            tenth = min(h.score for h in without if h.kind not in ("page", "fact"))
            assert entered.relevance * 1.2 >= tenth, q["question"]
    assert "url_for" not in {h.name for h in query.search(conn, "database connection pooling")}
    test_identifier_definitions_at_rank_one(conn)
