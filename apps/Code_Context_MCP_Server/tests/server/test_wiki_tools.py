"""read_wiki: a page as the core reads it, the list of pages, caps and refusals."""

import re

import pytest

from golestan_code_mcp import db
from golestan_code_mcp.wiki import read
from golestan_code_mcp.config import load

from server.helpers import call


def test_read_wiki_matches_core(pages):
    with db.connect(load()) as conn:
        page = read.read(conn, "pkg", pages[0])
    result = call("read_wiki", page="pkg", repo=pages[0])
    got = result["page"]
    assert result["status"] == "ok" and result["pages"] == [] and result["truncated"] is False
    assert (got["name"], got["repo"], got["directory"], got["language"], got["state"], got["compiler"],
            got["stale_reason"], got["symbols"], got["text"], got["truncated"]) == (
        page.name, page.repo, page.directory, page.language, page.state, page.compiler, page.stale_reason,
        page.symbols, page.text, page.truncated)
    assert re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ", got["compiled_at"])
    assert [(c["role"], c["path"], c["start_line"], c["end_line"], c["commit"], c["current_commit"])
            for c in got["citations"]] == [
        (c.role, c.path, c.start_line, c.end_line, c.recorded_commit, c.current_commit) for c in page.citations]
    files = [c for c in got["citations"] if c["kind"] == "file"]
    assert files and all(c["name"] == c["path"].rsplit("/", 1)[-1] and c["start_line"] is None for c in files)


def test_read_wiki_lists_the_pages(pages):
    with db.connect(load()) as conn:
        expected = [{"name": p.name, "repo": p.repo, "state": p.state, "summary": p.summary}
                    for p in read.pages(conn, pages[0])]
    assert call("read_wiki", repo=pages[0]) == {
        "status": "ok", "reason": None, "page": None, "pages": expected, "truncated": False}


def test_read_wiki_list_is_capped(pages, monkeypatch):
    with db.connect(load()) as conn:
        one = read.pages(conn, pages[0])[0]
    monkeypatch.setattr(read, "pages", lambda conn, repo=None: [one] * 201)
    result = call("read_wiki")
    assert len(result["pages"]) == 200 and result["truncated"] is True


@pytest.mark.parametrize(("arguments", "reason"), [
    ({"page": "pkg", "repo": "t-missing"}, "no repository named 't-missing'"),
    ({"page": "t_no_such_page"}, "no wiki page named 't_no_such_page'"),
])
def test_read_wiki_refusals_are_results(pages, arguments, reason):
    assert call("read_wiki", **arguments) == {
        "status": "unavailable", "reason": reason, "page": None, "pages": [], "truncated": False}


def test_read_wiki_ambiguous_name_asks_for_repo(pages):
    result = call("read_wiki", page="pkg")
    assert result["status"] == "unavailable" and result["page"] is None
    assert re.fullmatch(r"wiki page 'pkg' is in more than one repository: .+; pass repo", result["reason"])
    assert all(n in result["reason"] for n in pages)


def test_read_wiki_empty_page_refused_before_connecting(monkeypatch):
    monkeypatch.setenv("DB_PORT", "1")
    assert call("read_wiki", page="  ") == {
        "status": "unavailable", "reason": "the page name is empty", "page": None, "pages": [], "truncated": False}
