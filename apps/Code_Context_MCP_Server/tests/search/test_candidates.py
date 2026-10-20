"""The keyword query: every word escaped, operator words and special characters kept literal."""

import pytest

from golestan_code_mcp.search import candidates
from golestan_code_mcp.search import query

from search.helpers import A, LITERALS

pytestmark = pytest.mark.needs_model  # the shared `conn` then requires the embedding model


@pytest.mark.parametrize(("question", "expected"), [
    ("url_for", "{url_for}"),
    ("middleware chain", "{middleware} AND {chain}"),
    ("{x}", "{x}"),
    ("a\\b", "{ab}"),
    ("{} \\", ""),
])
def test_text_query_escapes_every_word(question, expected):
    assert candidates.text_query(question) == expected


@pytest.mark.parametrize(("question", "expected"), [
    ("requests routed to handlers", "$requests ACCUM $routed ACCUM $to ACCUM $handlers"),
    ("url_for redirect", "{url_for} ACCUM $redirect"),
    ("c&d (x)", "{c&d} ACCUM {(x)}"),
])
def test_hybrid_keyword_side_accepts_any_word(question, expected):
    assert candidates.text_query(question, every_word=False) == expected


@pytest.mark.parametrize("question", LITERALS)
def test_special_characters_are_literal(conn, repos, question):
    for mode in query.MODES:
        query.search(conn, question, [A], mode=mode)  # must not raise


def test_operator_words_stay_literal():
    assert candidates.text_query("NOT near and", every_word=False) == "{NOT} ACCUM {near} ACCUM {and}"
