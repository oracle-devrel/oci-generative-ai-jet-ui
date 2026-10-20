"""Reading the wiki: pages and read follow the contract, and unknown or ambiguous pages are refused."""

import uuid

import pytest

from golestan_code_mcp.wiki import compile
from golestan_code_mcp.wiki import read
from golestan_code_mcp.wiki import store

from wiki.helpers import functions, make_repo, text

pytestmark = pytest.mark.needs_model  # the shared `conn` then requires the embedding model


# --- reading -------------------------------------------------------------------------------------------------


def test_pages_and_read_follow_the_contract(conn, built):
    listed = read.pages(conn, built)
    assert [p.name for p in listed] == sorted(p.name for p in listed) and {p.repo for p in listed} == {built}
    pkg = next(p for p in listed if p.name == "pkg")
    assert (pkg.state, pkg.symbols, pkg.summary, pkg.stale_reason) == ("fresh", 10, "Widgets for the demo package.", None)
    page = read.read(conn, "pkg", built)
    assert (page.name, page.repo, page.directory, page.language, page.state, page.compiler, page.symbols) == (
        "pkg", built, "src/pkg", "python", "fresh", compile.COMPILER, 10)
    assert page.text == text(conn, built, "pkg") and not page.truncated
    order = ["key", "file", "depends", "uses", "calls"]
    keys = [(order.index(c.role), c.name) for c in page.citations]
    assert keys == sorted(keys)


def test_read_refuses_unknown_and_ambiguous_pages(conn, built, tmp_path):
    with pytest.raises(store.WikiError, match=f"^no wiki page named 'nope' in '{built}'$"):
        read.read(conn, "nope", built)
    with pytest.raises(store.WikiError, match="^no wiki page named 'nope'$"):
        read.read(conn, "nope")
    with pytest.raises(store.WikiError, match="^no repository named 't-missing'$"):
        read.pages(conn, "t-missing")
    unique = f"amb_{uuid.uuid4().hex[:6]}"
    names = sorted(make_repo(conn, tmp_path / f"r{i}", {f"{unique}/m.py": functions("a", 10)}) for i in range(2))
    with pytest.raises(store.WikiError) as e:
        read.read(conn, unique)
    assert str(e.value) == f"wiki page '{unique}' is in more than one repository: {names[0]}, {names[1]}; pass --repo"
    assert read.read(conn, unique, names[1]).repo == names[1]
