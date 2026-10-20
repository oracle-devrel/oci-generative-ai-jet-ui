"""The wiki compiler: which directories get a page, what a page says, and the citations behind it."""

import pytest

import posixpath
import re

from golestan_code_mcp.wiki import build as wiki_build
from golestan_code_mcp.wiki import compile
from golestan_code_mcp.wiki import read
from golestan_code_mcp.parsing import tables

from wiki.helpers import citation_rows, module_name, page_rows, rid, text

pytestmark = pytest.mark.needs_model  # the shared `conn` then requires the embedding model


# --- threshold and naming ------------------------------------------------------------------------------------


def test_one_page_per_directory_of_ten_named_definitions(conn, built):
    pages = page_rows(conn, built)
    assert {p[0]: p[1] for p in pages.values()} == {
        "src/pkg": "pkg", "src/pkg/sub": "pkg/sub", "tests": "tests", ".": built, "x": "x", "src/x": "src/x",
        "server": "server",
    }  # nine has 9 definitions plus line windows, docs only line windows: no page
    assert pages["pkg"][3] == 10 and pages["tests"][3] == 12 and pages["pkg"][2] == "python"
    assert pages["server"][2] == "go" and {p[7] for p in pages.values()} == {compile.COMPILER}
    assert {p[6] for p in pages.values()} == {"fresh"}


# --- the text ------------------------------------------------------------------------------------------------


def test_structure_purpose_and_sections(conn, built):
    page = text(conn, built, "pkg")
    assert page.startswith(
        "# pkg\n\n"
        "`pkg` is a Python package of 2 files and 10 definitions: 6 functions, 2 classes and 2 methods.\n"
        "Widgets for the demo package.\nCore widget code.\n\n## Key symbols\n"
        "- `Widget` (class): A widget, see Gadget for more.\n"
        "- `Gadget` (class): A gadget made by make_widget.\n"
        "- `make_widget` (function): Make a Widget instance.\n"
    )
    assert "- `Widget.stop` (method): no documentation\n" in page
    assert "## Depends on\n- `pkg/sub`: `sub_a`\n- Outside the index: `json`, `typing`\n" in page
    assert page.endswith("## Used by\n- `tests`\n")


def test_purpose_falls_back_to_types_then_to_the_stated_sentence(conn, built):
    assert "definitions: 9 functions and 1 class.\nA thing in x.\n" in text(conn, built, "x")
    sub = text(conn, built, "pkg/sub")
    assert "`pkg/sub` is a Python directory of 1 file and 10 definitions: 10 functions.\n" in sub
    assert "\nIts code has no documentation; the sections below come from its structure.\n" in sub
    assert sub.endswith("## Used by\n- `pkg`\n")


def test_go_page(conn, built):
    page = text(conn, built, "server")
    assert "`server` is a Go package of 1 file and 10 definitions: 8 functions, 1 method and 1 type.\n" in page
    assert "Package server serves widgets.\n" in page and "Copyright" not in page
    assert "- Outside the index: `fmt`, `net/http`\n" in page


def test_key_symbols_at_most_ten_ranked_by_outside_callers(conn, built):
    keys = re.findall(r"^- `([^`]+)` \(", text(conn, built, "tests"), re.M)
    assert len(keys) == 10
    page = text(conn, built, "tests")
    assert "## Depends on\n- `pkg`: `Widget`, `make_widget`\n" in page
    assert re.findall(r"^- `([^`]+)` \(", text(conn, built, "pkg"), re.M)[:3] == ["Widget", "Gadget", "make_widget"]


def test_no_path_or_line_number_in_any_page(conn, built):
    with conn.cursor() as cur:
        paths = [p for (p,) in cur.execute("select path from ccctx_files where repo_id = :r", r=rid(conn, built))]
    names = {posixpath.basename(p) for p in paths}
    assert any(n.endswith(tuple(tables.EXTENSIONS)) for n in names)
    for page in page_rows(conn, built).values():
        assert not any(n in page[4] for n in names | set(paths)), page[1]
        assert not re.search(r"line \d+", page[4]), page[1]


def test_every_named_symbol_and_module_is_cited(conn, built):
    for name, page in page_rows(conn, built).items():
        cited = read.read(conn, name, built).citations
        symbols = {c.name for c in cited if c.role in ("key", "calls")}
        modules = {module_name(c.name) for c in cited if c.role in ("depends", "uses")}
        outside = re.findall(r"`([^`]+)`", (re.findall(r"^- Outside the index: (.*)$", page[4], re.M) or [""])[0])
        keys = re.findall(r"^- `([^`]+)` \(", page[4], re.M)
        assert set(keys) <= {c.name for c in cited if c.role == "key"}, name
        for token in re.findall(r"`([^`]+)`", page[4]):
            assert token in symbols | modules | set(outside) | {name}, (name, token)
        assert {c.role for c in cited} >= {"key", "file"}


def test_citations_record_commit_and_hash_and_read_back_current_locations(conn, built):
    with conn.cursor() as cur:
        r = rid(conn, built)
        commit = cur.execute("select indexed_commit from ccctx_repos where id = :r", r=r).fetchone()[0]
        symbols = {sid: row for sid, *row in cur.execute(
            """select s.id, s.commit_sha, s.content_hash, f.path, s.start_line, s.end_line from ccctx_symbols s
                 join ccctx_files f on f.id = s.file_id where f.repo_id = :r""", r=r)}
        files = {fid: row for fid, *row in cur.execute(
            "select id, content_hash, path from ccctx_files where repo_id = :r", r=r)}
    rows = citation_rows(conn, built)
    assert rows
    for _, role, _, kind, sha, digest, symbol_id, file_id in rows:
        if role in ("key", "calls"):
            assert (sha, digest) == tuple(symbols[symbol_id][:2]) and file_id is None
        else:
            assert (sha, digest, kind) == (commit, files[file_id][0], "file") and symbol_id is None
    for name in page_rows(conn, built):
        for c in read.read(conn, name, built).citations:
            assert c.repo == built and c.current_commit == c.recorded_commit
            assert c.path is not None
            if c.role in ("key", "calls"):
                found = [s for s in symbols.values() if (s[2], s[3]) == (c.path, c.start_line)]
                assert found and found[0][4] == c.end_line
            else:
                assert c.path == c.name and c.start_line is None


# --- language coverage (012): key symbols rank by the stored visibility ---


def test_key_symbols_rank_by_the_stored_exported_flag(conn, fresh):
    name, _ = fresh
    keys = re.findall(r"^- `([^`]+)` \(", text(conn, name, name), re.M)
    assert keys[0] == "r0"  # ties (no callers, no docs) fall to the name
    with conn.cursor() as cur:
        cur.execute("""update ccctx_symbols set exported = false where name = 'r0' and file_id in
                         (select id from ccctx_files where repo_id = :r and path = 'root.py')""", r=rid(conn, name))
    conn.commit()
    wiki_build.build(conn, name)
    assert re.findall(r"^- `([^`]+)` \(", text(conn, name, name), re.M)[-1] == "r0"
