"""search: the ranked table, modes, filters, limits and refusals."""

import time

import pytest

from golestan_code_mcp import db
from golestan_code_mcp.search import model as search_model
from golestan_code_mcp.search import query
from golestan_code_mcp.config import load

from cli.helpers import FAKE_PW, run, table


def test_search_prints_ranked_table(ingested, capsys):
    n, _ = ingested
    code, out, _ = run(capsys, "search", "a", "--repo", n)
    rows = table(out)
    assert code == 0 and rows[0][:1] == ["1"] and rows[0][6] == "a"  # the definition of `a` comes first
    assert all(len(r[1].split(".")[1]) == 2 for r in rows)  # score with two decimals
    assert all(r[2] == "-" or r[2].isdigit() for r in rows) and all(r[3] == "-" or r[3].isdigit() for r in rows)


def test_search_shows_the_feedback_column(live, capsys, monkeypatch):
    hits = [query.Result(1, 48.0, 0.6, 1, 1, "flask", "function", "url_for", "src/flask/helpers.py", 1, 9, "python",
                            "def url_for():", relevance=40.0, feedback=0.2),
            query.Result(2, 30.0, 0.5, 2, 2, "flask", "function", "redirect", "src/flask/helpers.py", 10, 19,
                            "python", "def redirect():", relevance=30.0)]
    seen = []
    monkeypatch.setattr(query, "search", lambda *a, **k: seen.append(k.get("feedback", True)) or hits)
    code, out, _ = run(capsys, "search", "where is url_for")
    header, first, second = out.splitlines()
    assert code == 0 and header.split()[:3] == ["RANK", "SCORE", "FEEDBACK"]
    assert first.split()[:3] == ["1", "48.00", "+20%"] and second.split()[:3] == ["2", "30.00", "2"]  # blank at 0
    run(capsys, "search", "where is url_for", "--no-feedback")
    assert seen == [True, False]


@pytest.mark.parametrize(("mode", "keyword_dash", "semantic_dash"), [("text", False, True), ("vector", True, False)])
def test_search_modes(ingested, capsys, mode, keyword_dash, semantic_dash):
    n, _ = ingested
    code, out, _ = run(capsys, "search", "class", "--repo", n, "--mode", mode)
    rows = table(out)
    assert code == 0 and rows
    assert all((r[2] == "-") == keyword_dash and (r[3] == "-") == semantic_dash for r in rows)


def test_search_unknown_mode_refused_before_connecting(capsys, monkeypatch):
    monkeypatch.setenv("DB_PORT", "1")
    code, out, err = run(capsys, "search", "url_for", "--mode", "bogus")
    assert code == 1 and out == "" and "valid modes: vector, text, hybrid" in err


def test_search_repo_flags_narrow(ingested, capsys, monkeypatch):
    n, _ = ingested
    seen = []
    monkeypatch.setattr(query, "search", lambda conn, question, repos=None, mode="hybrid", env=None,
                        language=None, limit=10, **_: seen.append((repos, mode)) or [])
    run(capsys, "search", "x", "--repo", n, "--repo", f"{n},gin", "--repo", n)
    run(capsys, "search", "x")
    assert seen == [([n, "gin"], "hybrid"), (None, "hybrid")]


@pytest.mark.parametrize(("mode", "message"), [
    ("vector", "no symbols similar enough (similarity >= 0.30)"),
    ("hybrid", "no matching symbols"),
    ("text", "no matching symbols"),
])
def test_search_empty_results(ingested, capsys, monkeypatch, mode, message):
    n, _ = ingested
    monkeypatch.setattr(query, "search", lambda *args, **kwargs: [])
    code, out, _ = run(capsys, "search", "recipe for sourdough bread", "--repo", n, "--mode", mode)
    assert code == 0 and out.strip() == message


@pytest.mark.parametrize("question", ["", "   "])
def test_search_empty_question_refused_before_connecting(capsys, monkeypatch, question):
    monkeypatch.setenv("DB_PORT", "1")
    code, out, err = run(capsys, "search", question)
    assert code == 1 and out == "" and "question" in err


def test_search_unknown_repo(model, capsys):
    code, _, err = run(capsys, "search", "routing", "--repo", "t-missing")
    assert code == 1 and "no repository named 't-missing'" in err


def test_search_missing_model_hint(live, capsys, monkeypatch):
    monkeypatch.setattr(search_model, "INDEX", "NOT_AN_INDEX")
    code, _, err = run(capsys, "search", "routing")
    assert code == 1 and "ccctx model load" in err


def test_search_unreachable_exits_2(capsys, monkeypatch):
    monkeypatch.setenv("DB_PORT", "1")
    monkeypatch.setenv("DB_PASSWORD", FAKE_PW)
    started = time.monotonic()
    code, out, err = run(capsys, "search", "routing")
    assert time.monotonic() - started < 5 and code == 2 and FAKE_PW not in out + err


def test_search_language_and_limit_match_core(ingested, capsys):
    n, _ = ingested
    code, out, _ = run(capsys, "search", "a", "--repo", n, "--language", "python", "--limit", "2")
    with db.connect(load()) as conn:
        expected = query.search(conn, "a", [n], language="python", limit=2)
    assert code == 0 and [(r[0], r[6], r[7]) for r in table(out)] == [(str(h.rank), h.name, h.path) for h in expected]
    assert 1 <= len(expected) <= 2


def test_search_language_and_limit_reach_the_core(capsys, monkeypatch, live):
    seen = []
    monkeypatch.setattr(query, "search", lambda conn, question, repos=None, mode="hybrid", env=None,
                        language=None, limit=10, **_: seen.append((language, limit)) or [])
    run(capsys, "search", "x", "--language", "go", "--limit", "3")
    run(capsys, "search", "x")
    assert seen == [("go", 3), (None, 10)]


@pytest.mark.parametrize(("argv", "message"), [
    (["--limit", "0"], "limit must be between 1 and 50"),
    (["--limit", "51"], "limit must be between 1 and 50"),
    (["--limit", "ten"], "limit must be between 1 and 50"),
    (["--language", "cobol"], f"unknown language 'cobol'; valid languages: {', '.join(query.LANGUAGES)}"),
])
def test_search_bad_language_or_limit_refused_before_connecting(capsys, monkeypatch, argv, message):
    monkeypatch.setenv("DB_PORT", "1")
    code, out, err = run(capsys, "search", "routing", *argv)
    assert code == 1 and out == "" and err.strip() == f"error: {message}"


def test_search_shows_page_rows(live, capsys, monkeypatch):
    page = query.Result(1, 41.7, 0.63, 1, 1, "flask", "page", "flask/json", "src/flask/json", None, None,
                           "python", "# flask/json", "stale")
    monkeypatch.setattr(query, "search", lambda *a, **k: [page])
    code, out, _ = run(capsys, "search", "what does the json module do")
    row = out.splitlines()[1]
    assert code == 0 and "page (stale)" in row and row.split()[-1] == "-" and "src/flask/json" in row
