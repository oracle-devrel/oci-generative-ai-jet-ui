"""Wiki pages among the hits: where each is placed, module questions, states and filters."""

import pytest

from golestan_code_mcp.search import query
from golestan_code_mcp.search import ranking

from search.helpers import A, LEDGER_TEXT, hit

pytestmark = pytest.mark.needs_model  # the shared `conn` then requires the embedding model


def test_pages_go_above_the_first_hit_they_beat_on_similarity():
    rest = [hit("a", 0.8), hit("b", 0.5), hit("c", None)]
    placed = ranking._place(rest, [hit("p", 0.6), hit("q", 0.9)])
    assert [h["rowid"] for h in placed] == ["q", "a", "p", "b", "c"]


def test_a_page_without_similarity_goes_last():
    assert [h["rowid"] for h in ranking._place([hit("a", 0.4), hit("b", None)], [hit("p", None)])] == ["a", "b", "p"]


def test_a_module_question_puts_its_page_first(conn, ledger):
    results = query.search(conn, "what does the ledger module do", [ledger])
    assert results[0].kind == "page" and results[0].name == "ledger"
    assert {r.name for r in results[1:]} <= {"post_entry", "balance_of"}


def test_a_page_hit_has_its_directory_no_lines_and_its_state(conn, ledger):
    page = query.search(conn, "what does the ledger module do", [ledger])[0]
    assert (page.repo, page.path, page.start_line, page.end_line) == (ledger, "src/ledger", None, None)
    assert page.language == "python" and page.state == "fresh"
    assert page.snippet == "\n".join(LEDGER_TEXT.split("\n")[:10])
    assert page.similarity is not None and page.score > 0


def test_symbol_hits_have_no_state(conn, ledger):
    assert {r.state for r in query.search(conn, "what does the ledger module do", [ledger]) if r.kind != "page"} \
        <= {None}


def test_identifier_definitions_stay_above_pages(conn, ledger):
    results = query.search(conn, "post_entry", [ledger])
    assert results[0].name == "post_entry" and results[0].kind == "function"


def test_repo_and_language_filters_apply_to_pages(conn, ledger):
    question = "what does the ledger module do"
    assert all(r.kind != "page" for r in query.search(conn, question, [A]))
    assert all(r.kind != "page" for r in query.search(conn, question, [ledger], language="go"))
    assert query.search(conn, question, [ledger], language="python")[0].kind == "page"


def test_an_unrelated_question_finds_no_page(conn, ledger):
    assert all(r.kind != "page" for r in query.search(conn, "recipe for sourdough bread", [ledger]))


def test_a_stale_page_is_found_as_stale(conn, ledger):
    with conn.cursor() as cur:
        cur.execute("update ccctx_wiki_pages set state = 'stale' where name = 'ledger'")
    conn.commit()
    try:
        assert query.search(conn, "what does the ledger module do", [ledger])[0].state == "stale"
    finally:
        with conn.cursor() as cur:
            cur.execute("update ccctx_wiki_pages set state = 'fresh' where name = 'ledger'")
        conn.commit()


def test_without_the_page_index_search_returns_symbols_only(conn, ledger, monkeypatch):
    from golestan_code_mcp.wiki import store

    monkeypatch.setattr(store, "INDEX", "NOT_AN_INDEX")
    results = query.search(conn, "what does the ledger module do", [ledger])
    assert results and all(r.kind != "page" for r in results)


@pytest.mark.parametrize(("question", "page", "named"), [
    ("what does the json module do", "flask/json", True),
    ("what does the binding package do", "binding", True),
    ("explain package render", "render", True),
    ("what is in the sansio directory", "flask/sansio", True),
    ("how does Flask decide which view handles a request", "flask", False),
    ("how is json encoded", "flask/json", False),
    ("what does the jsonify module do", "flask/json", False),
])
def test_a_question_names_a_module_only_with_module_words(question, page, named):
    assert ranking.names_module(question, page) is named


def test_a_named_module_page_ranks_first_after_definitions(conn, ledger):
    results = query.search(conn, "what does the ledger package do", [ledger])
    assert results[0].kind == "page"
    assert query.search(conn, "post_entry", [ledger])[0].name == "post_entry"
