"""Import resolution: the indexed files each import reaches, and the outside packages that reach none."""

import pytest

from golestan_code_mcp import registry
from golestan_code_mcp.graph import imports as graph_imports

from graph.helpers import APP, H, TEST, imports

pytestmark = pytest.mark.needs_model  # the shared `conn` then requires the embedding model


def test_imports_resolve_within_the_repository(conn, repos):
    assert imports(conn, repos[0]) == [
        (APP, H),  # from . import helpers (relative)
        (TEST, "src/lib/__init__.py"),  # import lib, under the src/ source root
        (TEST, APP),  # from lib.app import Flask: the member falls back to its module
    ]  # import json is the standard library, not src/lib/... or any json package
    assert imports(conn, repos[1]) == [
        ("main.go", "util/a.go"), ("main.go", "util/b.go"),  # one row per file of the package directory
        ("util/a.go", "main.go"),  # the module root package
        ("web/app.js", "web/lib.js"),  # ./lib, with the .js suffix tried
    ]


def test_external_imports_name_what_resolves_to_no_indexed_file(conn, ext):
    with conn.cursor() as cur:
        rid = registry.repo_id(conn, ext)
        paths = dict(cur.execute("select id, path from ccctx_files where repo_id = :r", r=rid).fetchall())
        found = graph_imports.external_imports(cur, rid)
    assert {paths[fid]: names for fid, names in found.items() if names} == {
        # the first dotted component; relative imports (resolved or not) and pkg.other (indexed) never count
        "src/pkg/mod.py": {"json", "werkzeug", "typing"},
        # the full import path; the repository's own module path example.com/m... never counts
        "main.go": {"fmt", "net/http"},
    }


def test_external_imports_of_the_graph_repositories(conn, repos):
    py, go = repos
    with conn.cursor() as cur:
        for name, expected in ((py, {H: {"json"}}), (go, {"main.go": {"fmt"}})):
            rid = registry.repo_id(conn, name)
            paths = dict(cur.execute("select id, path from ccctx_files where repo_id = :r", r=rid).fetchall())
            assert {paths[f]: n for f, n in graph_imports.external_imports(cur, rid).items() if n} == expected


# --- language coverage (012): resolution helpers ---


def test_suffix_index_maps_every_path_suffix():
    index = graph_imports._suffix_index({"src/com/acme/Order.java": 1, "lib/Order.java": 2, "a.h": 3})
    assert index["src/com/acme/Order.java"] == [1] and index["com/acme/Order.java"] == [1]
    assert sorted(index["Order.java"]) == [1, 2] and index["a.h"] == [3]
    assert "src" not in index and "com/acme" not in index  # files only, never folders


def test_files_carry_their_namespaces(conn, repos):
    with conn.cursor() as cur:
        files = graph_imports._files(cur, {"r": registry.repo_id(conn, repos[0])})
    assert files and all(len(v) == 3 and v[2] is None for v in files.values())
