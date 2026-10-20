"""Graph queries: callers, calls, impact and definitions, their limits and refusals."""

import pytest

from golestan_code_mcp import registry
from golestan_code_mcp.graph import queries

from graph.helpers import APP, CHAIN, DEFS, H, OTHER, TEST, rows

pytestmark = pytest.mark.needs_model  # the shared `conn` then requires the embedding model


def test_callers_of_a_bare_name_cover_every_definition(conn, repos):
    found = queries.callers(conn, "url_for", repos=repos)
    assert {r.repo for r in found} == {repos[0]}
    assert rows(found, "name", "kind", "path", "line", "callee") == [
        ("Flask.url_for", "method", APP, 6, "url_for"),
        ("Flask.open", "method", APP, 9, "Flask.url_for"),
        ("Other.run", "method", OTHER, 6, "Other.url_for"),
        ("(module)", "file", TEST, 4, "url_for"),
        ("obj_call", "function", TEST, 12, "Flask.url_for"),
        ("class_call", "function", TEST, 16, "Flask.url_for"),
    ]


def test_qualified_name_narrows_to_the_method(conn, repos):
    assert rows(queries.callers(conn, "Flask.url_for", repos=repos), "name") == [("Flask.open",), ("obj_call",), ("class_call",)]


def test_calls(conn, repos):
    found = queries.calls(conn, "url_for", repos=repos)
    assert rows(found, "caller", "line", "name", "kind", "path", "start_line", "end_line") == [
        ("Flask.url_for", 6, "url_for", "function", H, 4, 5),
        ("url_for", 5, "encode", "function", H, 8, 10),
    ]
    assert queries.calls(conn, "encode", repos=repos) == []  # only the standard library


def test_impact_hops(conn, repos):
    assert rows(queries.impact(conn, "a", 3, repos=repos), "hops", "name") == [(1, "b"), (1, "c"), (2, "d"), (3, "e")]  # diamond: c 1
    assert rows(queries.impact(conn, "a", 2, repos=repos), "hops", "name") == [(1, "b"), (1, "c"), (2, "d")]
    one = queries.impact(conn, "a", 1, repos=repos)
    assert {r.name for r in one} == {r.name for r in queries.callers(conn, "a", repos=repos)}
    assert rows(queries.impact(conn, "ping", repos=repos), "hops", "name") == [(1, "pong"), (2, "ping")]  # a cycle, once each
    assert rows(queries.impact(conn, "fact", repos=repos), "hops", "name", "kind", "path", "start_line", "end_line") == [
        (1, "fact", "function", CHAIN, 29, 30)]


@pytest.mark.parametrize("question", ["callers", "calls", "impact"])
def test_refusals(conn, repos, question):
    ask = getattr(queries, question)
    with pytest.raises(ValueError, match="no symbol named 'nope'"):
        ask(conn, "nope")
    for empty in ("", "   "):
        with pytest.raises(ValueError, match="the name is empty"):
            ask(conn, empty)
    with pytest.raises(ValueError, match="no symbol named 'helper'"):  # only in the other repository
        ask(conn, "helper", repos=[repos[0]])
    with pytest.raises(registry.RegistryError, match="no repository named 't-missing'"):
        ask(conn, "a", repos=["t-missing"])


@pytest.mark.parametrize("depth", [0, 6, -1])
def test_depth_out_of_range(conn, repos, depth):
    with pytest.raises(ValueError, match="depth must be between 1 and 5"):
        queries.impact(conn, "a", depth, repos=repos)


def test_repos_limit_every_question(conn, repos):
    py, go = repos
    assert rows(queries.callers(conn, "a", repos=[py]), "name") == [("b",), ("c",)]
    assert queries.callers(conn, "a", repos=[go]) == []  # the JavaScript a has no callers
    assert rows(queries.callers(conn, "a", repos=repos), "name") == [("b",), ("c",)]  # both repositories
    assert {("b",), ("c",)} <= set(rows(queries.callers(conn, "a"), "name"))  # all by default
    assert rows(queries.calls(conn, "a", repos=[go]), "caller", "name") == [("a", "helper")]
    assert queries.calls(conn, "a", repos=[py]) == []
    assert rows(queries.impact(conn, "helper", 3, repos=[go]), "hops", "name") == [(1, "start"), (1, "a")]
    assert rows(queries.callers(conn, "Helper", repos=repos), "repo", "name") == [(go, "main"), (go, "Other")]


def test_definitions_qualified_name_returns_that_definition_with_its_source(conn, repos):
    found, total = queries.definitions(conn, "Flask.url_for", repos=repos)
    assert total == 1
    assert rows(found, "name", "kind", "repo", "path", "start_line", "end_line", "cut") == [
        ("Flask.url_for", "method", repos[0], APP, 5, 6, False)]
    assert found[0].source == "    def url_for(self, x):\n        return helpers.url_for(x)"


def test_definitions_bare_name_returns_the_function_and_the_methods(conn, repos):
    found, total = queries.definitions(conn, "url_for", repos=repos)
    assert total == 3
    assert rows(found, "name", "kind", "path", "start_line") == [
        ("Flask.url_for", "method", APP, 5),
        ("url_for", "function", H, 4),
        ("Other.url_for", "method", OTHER, 2),
    ]
    assert found[1].source == "def url_for(x):\n    return encode(x)"


def test_definitions_repos_limit_the_matches(conn, repos, defs):
    py, go = repos
    assert rows(queries.definitions(conn, "a", repos=[go])[0], "repo", "path") == [(go, "web/lib.js")]
    assert rows(queries.definitions(conn, "a", repos=[py])[0], "path") == [(CHAIN,), (OTHER,)]
    with pytest.raises(ValueError, match="no symbol named 'helper'"):  # only in the other repository
        queries.definitions(conn, "helper", repos=[py])
    with pytest.raises(registry.RegistryError, match="no repository named 't-missing'"):  # refused before the name
        queries.definitions(conn, "nope", repos=["t-missing"])


def test_definitions_cap_at_five_in_repo_path_line_order(conn, repos, defs):
    py = repos[0]
    every = sorted([
        (defs, "pkg/a.py", 2, "A.run"), (defs, "pkg/a.py", 7, "B.run"), (defs, "pkg/a.py", 11, "run"),
        (defs, "pkg/b.py", 1, "run"), (defs, "pkg/b.py", 6, "C.run"), (defs, "pkg/c.py", 1, "run"),
        (py, OTHER, 5, "Other.run"),
    ])
    found, total = queries.definitions(conn, "run", repos=[py, defs])
    assert total == 7
    assert rows(found, "repo", "path", "start_line", "name") == every[:5]
    assert queries.definitions(conn, "run", repos=[defs])[1] == 6


def test_definitions_cut_a_long_source_at_400_lines(conn, defs):
    found, total = queries.definitions(conn, "big", repos=[defs])
    assert total == 1
    (big,) = found
    assert (big.start_line, big.end_line, big.cut) == (1, 450, True)
    assert big.source == "\n".join(DEFS["pkg/big.py"].splitlines()[:400])
    assert queries.definitions(conn, "C.run", repos=[defs])[0][0].cut is False


def test_definitions_refusals(conn, repos, defs):
    with conn.cursor() as cur:
        cur.execute("""select s.name from ccctx_symbols s join ccctx_files f on f.id = s.file_id
                         join ccctx_repos r on r.id = f.repo_id where r.name = :n and s.kind = 'chunk'""", n=defs)
        (window,) = [n for (n,) in cur]  # notes.md:1-3
    for name in (window, window.rsplit(".", 1)[1]):  # line windows never match, exactly or as a bare suffix
        with pytest.raises(ValueError, match="no symbol named"):
            queries.definitions(conn, name, repos=[defs])
    with pytest.raises(ValueError, match="no symbol named 'nope'"):
        queries.definitions(conn, "nope", repos=repos)
    for empty in ("", "   "):
        with pytest.raises(ValueError, match="the name is empty"):
            queries.definitions(conn, empty, repos=repos)
