"""Wiki builds: building, rebuilding and refusing; marking pages stale and recompiling them."""

import json
import logging
import uuid

import pytest

from golestan_code_mcp import registry
from golestan_code_mcp.wiki import build as wiki_build
from golestan_code_mcp.wiki import read
from golestan_code_mcp.wiki import store

from wiki.helpers import citation_rows, execute, make_repo, mark, page_rows, rid, symbol_of, text

pytestmark = pytest.mark.needs_model  # the shared `conn` then requires the embedding model


# --- build behavior ------------------------------------------------------------------------------------------


def test_second_build_is_idempotent_and_keeps_search_text(conn, fresh):
    name, _ = fresh
    with conn.cursor() as cur:  # a marker the build would overwrite if it rewrote search_text
        cur.execute("update ccctx_wiki_pages set search_text = 'marker' where repo_id = :r", r=rid(conn, name))
    conn.commit()
    pages, cites = page_rows(conn, name), citation_rows(conn, name)
    [counts] = wiki_build.build(conn, name)
    assert (counts.repo, counts.pages, counts.added, counts.updated, counts.removed) == (name, 7, 0, 0, 0)
    assert page_rows(conn, name) == pages and citation_rows(conn, name) == cites
    assert {p[5] for p in pages.values()} == {"marker"}


def test_first_build_counts_and_sets_wiki_at(conn, tmp_path):
    name = make_repo(conn, tmp_path / "repo", build=False)
    with conn.cursor() as cur:
        assert cur.execute("select wiki_at from ccctx_repos where name = :n", n=name).fetchone()[0] is None
    [counts] = wiki_build.build(conn, name)
    assert (counts.pages, counts.added, counts.updated, counts.removed) == (7, 7, 0, 0)
    with conn.cursor() as cur:
        assert cur.execute("select wiki_at from ccctx_repos where name = :n", n=name).fetchone()[0] is not None
    assert page_rows(conn, name)["pkg"][5] == f"page pkg in src/pkg\n{text(conn, name, 'pkg')}"


def test_unknown_and_unindexed_repositories_refused(conn, tmp_path):
    with pytest.raises(store.WikiError, match="^no repository named 't-missing'$"):
        wiki_build.build(conn, "t-missing")
    (tmp_path / "empty").mkdir()
    name = f"t-{uuid.uuid4().hex[:8]}"
    registry.add_repo(conn, tmp_path / "empty", name)
    with pytest.raises(store.WikiError) as e:
        wiki_build.build(conn, name)
    assert str(e.value) == f"repository '{name}' is not indexed yet; run `ccctx ingest {name}`"


def test_page_index_exists_after_a_build(conn, built):
    with conn.cursor() as cur:
        assert cur.execute("select count(*) from user_indexes where index_name = :i", i=store.INDEX).fetchone()[0]
        assert store.ensure_index(cur)


def test_build_logs_one_record_per_repository(conn, fresh, caplog):
    name, _ = fresh
    with caplog.at_level(logging.INFO, logger="golestan_code_mcp.wiki"):
        wiki_build.build(conn, name)
    records = [json.loads(r.getMessage()) for r in caplog.records if r.name == "golestan_code_mcp.wiki"]
    assert len(records) == 1 and records[0]["event"] == "wiki" and records[0]["repo"] == name
    assert (records[0]["built"], records[0]["stale"], records[0]["removed"]) == (7, 0, 0)
    assert isinstance(records[0]["ms"], int) and "text" not in records[0]


def test_mark_stale_names_the_changed_or_gone_symbol(conn, fresh):
    name, _ = fresh
    sid, old = symbol_of(conn, name, "Widget")
    execute(conn, "update ccctx_symbols set commit_sha = :c where id = :i", c="a" * 40, i=sid)
    gone, _ = symbol_of(conn, name, "x0")
    execute(conn, "delete from ccctx_symbols where id = :i", i=gone)
    marked = mark(conn, name)
    changed = f"Widget changed ({old[:12]} -> {'a' * 12})"
    assert marked == [("pkg", changed), ("tests", changed), ("x", "x0 is gone")]  # tests calls Widget
    states = {n: (p[6], p[8]) for n, p in page_rows(conn, name).items()}
    assert states["pkg"] == ("stale", changed) and states["x"] == ("stale", "x0 is gone")
    assert {s for n, s in states.items() if n not in ("pkg", "tests", "x")} == {("fresh", None)}
    assert mark(conn, name) == []  # only fresh pages are marked


def test_a_rewritten_symbol_is_reported_as_changed(conn, fresh):
    name, _ = fresh
    sid, old = symbol_of(conn, name, "x0")
    with conn.cursor() as cur:  # what ingestion does to an edited symbol: delete it, insert it again
        cur.execute("""insert into ccctx_symbols (file_id, name, kind, start_line, end_line, source, content_hash,
                                                  commit_sha)
                       select file_id, name, kind, start_line, end_line, source, :h, :c
                         from ccctx_symbols where id = :i""", h="b" * 64, c="b" * 40, i=sid)
        cur.execute("delete from ccctx_symbols where id = :i", i=sid)
    conn.commit()
    assert ("x", f"x0 changed ({old[:12]} -> {'b' * 12})") in mark(conn, name)


def test_refresh_recompiles_adds_and_removes(conn, fresh):
    name, _ = fresh
    sid, _ = symbol_of(conn, name, "Widget")
    execute(conn, "update ccctx_symbols set commit_sha = :c where id = :i", c="b" * 40, i=sid)
    marked = mark(conn, name)
    with conn.cursor() as cur:  # x drops to 9 definitions, nine reaches 10
        cur.execute("""delete from ccctx_symbols where id = (select s.id from ccctx_symbols s
                         join ccctx_files f on f.id = s.file_id where f.repo_id = :r and s.name = 'x1')""",
                    r=rid(conn, name))
        fid = cur.execute("select id from ccctx_files where repo_id = :r and path = 'nine/mod.py'",
                          r=rid(conn, name)).fetchone()[0]
        cur.execute("""insert into ccctx_symbols (file_id, name, kind, start_line, end_line, content_hash, commit_sha,
                         search_text, source) values (:f, 'n9', 'function', 40, 41, :h, :c, 'function n9', 'def n9()')""",
                    f=fid, h="0" * 64, c="b" * 40)
    conn.commit()
    report = wiki_build.refresh(conn, rid(conn, name))
    # pkg and tests, and src/x: without the clash it is renamed x
    assert (report.recompiled, report.added, report.removed, report.error) == (3, 1, 1, None)
    assert report.stale == marked
    pages = page_rows(conn, name)
    assert pages["x"][0] == "src/x" and "src/x" not in pages
    assert pages["nine"][6] == "fresh" and pages["nine"][3] == 10
    assert pages["pkg"][6:9:2] == ("fresh", marked[0][1])  # the reason is kept after the recompile
    widget = [c for c in read.read(conn, "pkg", name).citations if c.name == "Widget"][0]
    assert widget.recorded_commit == "b" * 40 == widget.current_commit


def test_failed_refresh_leaves_pages_stale(conn, fresh, monkeypatch):
    name, _ = fresh
    for symbol in ("Widget", "r0"):
        sid, _ = symbol_of(conn, name, symbol)
        execute(conn, "update ccctx_symbols set commit_sha = :c where id = :i", c="c" * 40, i=sid)
    assert len(mark(conn, name)) == 3  # pkg, tests and the root
    real, calls = store._write_page, []

    def fail_second(*args, **kwargs):
        calls.append(1)
        if len(calls) == 2:
            raise RuntimeError("database went away")
        return real(*args, **kwargs)

    monkeypatch.setattr(store, "_write_page", fail_second)
    report = wiki_build.refresh(conn, rid(conn, name))
    assert report.error and "database went away" in report.error and report.recompiled == 0
    states = {n: p[6] for n, p in page_rows(conn, name).items()}
    assert states["pkg"] == states[name] == "stale"


def test_repository_without_a_wiki_is_untouched(conn, tmp_path):
    name = make_repo(conn, tmp_path / "repo", build=False)
    assert mark(conn, name) == []
    report = wiki_build.refresh(conn, rid(conn, name))
    assert (report.stale, report.recompiled, report.added, report.removed, report.error) == ([], 0, 0, 0, None)
    assert page_rows(conn, name) == {}
