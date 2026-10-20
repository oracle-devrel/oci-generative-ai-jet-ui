"""The search: refused input, ranking by name and meaning, modes and repository scope."""

import re

import pytest

from golestan_code_mcp import registry
from golestan_code_mcp.search import query
from golestan_code_mcp.search import ranking
from golestan_code_mcp.parsing import tables

from search.helpers import A, B, LANGUAGE_LIST, RUN, add_symbol, names

pytestmark = pytest.mark.needs_model  # the shared `conn` then requires the embedding model


# --- no database ------------------------------------------------------------------------------------------


@pytest.mark.parametrize("question", ["", "   "])
def test_empty_question_refused(question):
    with pytest.raises(ValueError, match="question"):
        query.search(None, question)


def test_unknown_mode_refused_before_searching():
    with pytest.raises(ValueError, match="valid modes: vector, text, hybrid"):
        query.search(None, "url_for", mode="bogus")


@pytest.mark.parametrize("limit", [0, 51, -1, 2.5, "3"])
def test_limit_outside_1_to_50_refused(limit):
    with pytest.raises(ValueError, match="^limit must be between 1 and 50$"):
        query.check_limit(limit)
    with pytest.raises(ValueError, match="^limit must be between 1 and 50$"):
        query.search(None, "url_for", limit=limit)


@pytest.mark.parametrize("limit", [1, 10, 50])
def test_limit_inside_1_to_50_accepted(limit):
    query.check_limit(limit)  # must not raise


def test_languages_are_the_chunkers_plus_text():
    assert sorted(query.LANGUAGES) == sorted({*tables.EXTENSIONS.values(), "text"})
    assert ", ".join(sorted(query.LANGUAGES)) == LANGUAGE_LIST


def test_unknown_language_refused_before_connecting(monkeypatch):
    monkeypatch.setenv("DB_PORT", "1")  # no connection is made: conn is None and the port is closed
    reason = "^" + re.escape(f"unknown language 'cobol'; valid languages: {LANGUAGE_LIST}") + "$"
    with pytest.raises(ValueError, match=reason):
        query.check_language("cobol")
    with pytest.raises(ValueError, match=reason):
        query.search(None, "url_for", language="cobol")
    for language in ("python", "go", "text"):
        query.check_language(language)  # must not raise


def test_question_then_limit_then_language_checked():
    with pytest.raises(ValueError, match="question"):
        query.search(None, "  ", language="cobol", limit=0)
    with pytest.raises(ValueError, match="limit"):
        query.search(None, "url_for", language="cobol", limit=0)


def test_definitions_rank_above_call_sites(conn, repos):
    results = query.search(conn, "url_for", [A])
    assert set(names(results)[:2]) == {"url_for", "App.url_for"}
    assert "redirect_home" in names(results)[2:]  # a call site: found, but after both definitions
    assert [r.rank for r in results] == list(range(1, len(results) + 1)) and len(results) <= query.LIMIT


def test_qualified_name_ranks_that_method_first(conn, repos):
    assert query.search(conn, "App.url_for", [A])[0].name == "App.url_for"


def test_case_does_not_matter(conn, repos):
    assert set(names(query.search(conn, "URL_FOR", [A]))[:2]) == {"url_for", "App.url_for"}


def test_no_boost_without_a_definition(conn, repos):
    results = query.search(conn, "endpoint", [A])  # appears in code, defined nowhere
    scores = [r.score for r in results]
    assert scores == sorted(scores, reverse=True)


def test_text_mode_needs_every_word(conn, repos):
    results = query.search(conn, "middleware chain", [B], mode="text")
    assert names(results) == ["handleChain"]  # Engine.Use has "middleware" but not "chain"
    assert results[0].keyword_rank == 1 and results[0].semantic_rank is None


def test_vector_mode_ranks_by_meaning_above_the_floor(conn, repos):
    results = query.search(conn, "how are incoming requests routed to handlers", [A], mode="vector")
    assert results[0].name == "route_request"
    assert all(r.similarity >= ranking.FLOOR and r.keyword_rank is None and r.semantic_rank for r in results)


def test_hybrid_results_explain_their_rank(conn, repos):
    results = query.search(conn, "url_for", [A])
    top = results[0]
    assert top.score > 0 and top.keyword_rank and top.semantic_rank
    assert all(r.keyword_rank or r.semantic_rank for r in results)


def test_repository_scoping(conn, repos):
    assert {r.repo for r in query.search(conn, "middleware", [B])} == {B}
    both = query.search(conn, "url for middleware", [A, B, A])
    assert {r.repo for r in both} <= {A, B} and both


def test_unknown_repo_refused(conn):
    with pytest.raises(registry.RegistryError, match="no repository named 't-missing'"):
        query.search(conn, "routing", [A, "t-missing"])


def test_fresh_commit_is_searchable_at_once(conn, repos):
    token = f"zebra_{RUN}"
    with conn.cursor() as cur:
        fid = cur.execute(
            "select f.id from ccctx_files f join ccctx_repos r on r.id = f.repo_id where r.name = :n and rownum = 1",
            n=A).fetchone()[0]
        add_symbol(cur, fid, token, "function", "pkg/fresh.py", f"def {token}():\n    pass\n")
    conn.commit()
    assert query.search(conn, token, [A], mode="text")[0].name == token  # SYNC (ON COMMIT)
