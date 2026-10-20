"""wiki build, list, show and citations, with their refusals."""

import re
import uuid

from golestan_code_mcp import db
from golestan_code_mcp.config import load

from cli.helpers import make_wiki_repo, run


def test_wiki_build_prints_one_line_per_repository(wikirepo, capsys):
    n, _, out, err = wikirepo
    assert re.fullmatch(rf"{n}: 1 pages \(1 added, 0 updated, 0 removed\) in \d+\.\ds\n", out)
    assert '"event": "wiki"' in err
    code, out, _ = run(capsys, "wiki", "build", "--repo", n)
    assert code == 0 and re.fullmatch(rf"{n}: 1 pages \(0 added, 0 updated, 0 removed\) in \d+\.\ds\n", out)


def test_wiki_build_notes_when_pages_are_not_searchable(wikirepo, capsys, monkeypatch):
    from golestan_code_mcp.wiki import store

    monkeypatch.setattr(store, "ensure_index", lambda cur: False)
    code, _, err = run(capsys, "wiki", "build", "--repo", wikirepo[0])
    assert code == 0 and "note: wiki pages are not searchable until you run `ccctx model load`" in err


def test_wiki_list_columns(wikirepo, capsys):
    n = wikirepo[0]
    code, out, _ = run(capsys, "wiki", "list", "--repo", n)
    header, *rows = out.splitlines()
    assert code == 0 and header.split() == ["NAME", "REPO", "STATE", "SYMBOLS", "COMPILED", "LAST", "STALE"]
    assert len(rows) == 1
    assert re.fullmatch(rf"pkg\s+{n}\s+fresh\s+10\s+\d{{4}}-\d\d-\d\d \d\d:\d\d:\d\d\s+-", rows[0])


def test_wiki_list_without_pages(live, capsys, monkeypatch):
    from golestan_code_mcp.wiki import read as wiki_read

    monkeypatch.setattr(wiki_read, "pages", lambda conn, repo=None: [])
    code, out, _ = run(capsys, "wiki", "list")
    assert code == 0 and out.strip() == "no wiki pages"


def test_wiki_show_prints_the_stored_text_then_sources(wikirepo, capsys):
    from golestan_code_mcp.wiki import read as wiki_read

    n = wikirepo[0]
    with db.connect(load()) as conn:
        page = wiki_read.read(conn, "pkg", n)
    code, out, _ = run(capsys, "wiki", "show", "pkg", "--repo", n)
    assert code == 0
    header, _, rest = out.partition("\n")
    assert re.fullmatch(rf"pkg \({n}, src/pkg\) fresh, compiled \d{{4}}-\d\d-\d\d \d\d:\d\d:\d\d by ccctx-wiki/1",
                        header)
    assert page.text.rstrip("\n") in rest
    sources = rest.split("## Sources\n", 1)[1].splitlines()
    assert len(sources) == len(page.citations)
    assert "- `post0` (function, key) src/pkg/core.py:" in rest
    assert "- `src/pkg/core.py` (file, file)" in rest


def test_wiki_citations_table(wikirepo, capsys):
    n = wikirepo[0]
    code, out, _ = run(capsys, "wiki", "citations", "pkg", "--repo", n)
    header, *rows = out.splitlines()
    assert code == 0 and header.split() == ["NAME", "KIND", "ROLE", "REPO", "PATH", "LINES", "COMPILED", "CURRENT"]
    key = next(r.split() for r in rows if r.split()[0] == "post0")
    assert key[1:5] == ["function", "key", n, "src/pkg/core.py"] and re.fullmatch(r"\d+-\d+", key[5])
    assert len(key[6]) == 12 and key[6] == key[7]
    file_row = next(r.split() for r in rows if r.split()[0] == "core.py")
    assert file_row[1:3] == ["file", "file"] and file_row[5] == "-"


def test_wiki_refusals_exit_1(wikirepo, capsys, tmp_path):
    n = wikirepo[0]
    assert run(capsys, "wiki", "show", "pkg", "--repo", "t-nope") == (1, "", "error: no repository named 't-nope'\n")
    assert run(capsys, "wiki", "show", "nope", "--repo", n)[2] == f"error: no wiki page named 'nope' in '{n}'\n"
    empty = f"t-{uuid.uuid4().hex[:8]}"
    (tmp_path / "e").mkdir()
    run(capsys, "repo", "add", str(tmp_path / "e"), "--name", empty)
    code, _, err = run(capsys, "wiki", "build", "--repo", empty)
    assert code == 1 and err == f"error: repository '{empty}' is not indexed yet; run `ccctx ingest {empty}`\n"


def test_wiki_ambiguous_page_needs_repo(wikirepo, capsys, tmp_path):
    other = f"t-{uuid.uuid4().hex[:8]}"
    run(capsys, "repo", "add", str(make_wiki_repo(tmp_path / "w2")), "--name", other)
    run(capsys, "ingest", other)
    run(capsys, "wiki", "build", "--repo", other)
    code, _, err = run(capsys, "wiki", "show", "pkg")
    listed = re.fullmatch(r"error: wiki page 'pkg' is in more than one repository: (.+); pass --repo\n", err)
    names = listed.group(1).split(", ")  # earlier tests' repositories have a `pkg` page too until teardown
    assert code == 1 and {wikirepo[0], other} <= set(names) and names == sorted(names)


def test_wiki_unreachable_exits_2(capsys, monkeypatch):
    monkeypatch.setenv("DB_PORT", "1")
    assert run(capsys, "wiki", "list")[0] == 2
