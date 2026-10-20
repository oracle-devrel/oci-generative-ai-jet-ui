"""Search filters and hits: language, limit, the opening snippet, and the defaults."""

import pytest

from golestan_code_mcp.search import query
from golestan_code_mcp.parsing import chunks

from search.helpers import A, C, SYMBOLS, TOKEN, in_language, names, opening

pytestmark = pytest.mark.needs_model  # the shared `conn` then requires the embedding model


@pytest.mark.parametrize("language", ["python", "go"])
def test_language_keeps_only_that_language(conn, repos, language):
    results = query.search(conn, TOKEN, [C], language=language, limit=50)
    assert sorted(names(results)) == sorted(in_language(C, language))
    assert {r.language for r in results} == {language}


def test_repo_and_language_still_fill_limit(conn, repos):
    # a 2-hit pool holds out-of-scope hits; widening must go on until `limit` in-scope hits are found
    results = query.search(conn, TOKEN, [C], language="go", limit=4, env={"CCCTX_SEARCH_CANDIDATES": "2"})
    assert sorted(names(results)) == sorted(in_language(C, "go"))


def test_limit_caps_the_hits(conn, repos):
    results = query.search(conn, TOKEN, [C], limit=3)
    assert len(results) == 3 and [r.rank for r in results] == [1, 2, 3]


def test_every_hit_has_its_language_and_opening_snippet(conn, repos):
    sources = {name: source for name, _, _, source in SYMBOLS[C]}
    results = query.search(conn, TOKEN, [C], limit=50)
    assert sorted(names(results)) == sorted(sources)
    for r in results:
        assert r.language == chunks.detect_language(r.path)
        assert r.snippet == opening(sources[r.name])
        assert len(r.snippet) <= 800 and r.snippet.count("\n") <= 9 and not r.snippet.endswith("\n")
    by_name = {r.name: r for r in results}
    assert by_name["tall"].snippet.count("\n") == 9  # 31 lines stored, 10 shown
    assert by_name["wide"].snippet == sources["wide"][:800]  # a 1000-character second line, cut at 800 characters


def test_defaults_give_the_same_hits_as_before(conn, repos):
    def key(results):
        return [(r.rank, r.name, r.score, r.keyword_rank, r.semantic_rank, r.similarity) for r in results]

    before = query.search(conn, "url_for", [A])
    assert key(query.search(conn, "url_for", [A], language=None, limit=query.LIMIT)) == key(before)
    assert key(query.search(conn, "url_for", [A], language="python")) == key(before)  # all of A is Python
