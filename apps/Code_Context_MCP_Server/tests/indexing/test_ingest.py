"""A full ingest: its summary and rows, re-ingesting, failures that keep the previous index, and refusals."""

import hashlib
import json
import logging

import pytest

from golestan_code_mcp import db
from golestan_code_mcp.indexing import files as indexing_files
from golestan_code_mcp.indexing import ingest as indexing_ingest
from golestan_code_mcp.indexing.files import IngestError
from golestan_code_mcp.indexing import write as indexing_write
from golestan_code_mcp.search import model
from golestan_code_mcp.search import query
from golestan_code_mcp.config import load

from indexing.helpers import APP_PY, ENV, head, register, revision, stored
from support import git

pytestmark = pytest.mark.needs_model  # the shared `conn` then requires the embedding model


def test_ingest_summary_and_rows(conn, repo, caplog):
    name = register(conn, repo)
    with caplog.at_level(logging.INFO, logger="golestan_code_mcp.ingest"):
        summary = indexing_ingest.ingest(conn, name, ENV)

    assert summary.commit == head(repo) and not summary.dirty
    assert summary.files == 7 and summary.scanned == 7 + sum(summary.skipped.values())
    assert (summary.no_grammar, summary.parse_errors) == (3, 1)  # .gitignore, notes.txt, empty.txt / broken.py

    rows = stored(conn, name)
    symbols = [r for r in rows if r[3] is not None]
    assert summary.symbols == len(symbols)
    assert {r[0] for r in rows} == {".gitignore", "app.py", "main.go", "web.js", "broken.py", "notes.txt", "empty.txt"}
    assert {r[9] for r in symbols} == {summary.commit}  # SC-006
    by_name = {r[3]: r for r in symbols}
    assert by_name["helper"][4:7] == ("function", 4, 5)
    assert by_name["Service.run"][4] == "method" and by_name["Service"][4] == "class"
    assert by_name["main"][4] == "function" and by_name["hello"][4] == "function"
    assert {r[3] for r in symbols if r[0] == "notes.txt"} == {"notes.txt:1-60", "notes.txt:51-110", "notes.txt:101-130"}
    assert {r[4] for r in symbols if r[0] == "broken.py"} == {"chunk"}
    for path, language, file_hash, _, _, start, end, source, symbol_hash, _ in symbols:
        assert file_hash == hashlib.sha256((repo / path).read_bytes()).hexdigest()
        assert symbol_hash == hashlib.sha256(source.encode()).hexdigest()
        assert source == "\n".join((repo / path).read_text(encoding="utf-8").splitlines()[start - 1:end])
    assert {r[0]: r[1] for r in rows}["app.py"] == "python"

    record = json.loads(next(r.getMessage() for r in caplog.records if r.name == "golestan_code_mcp.ingest"))
    assert record["event"] == "ingest" and record["commit"] == summary.commit and record["symbols"] == summary.symbols


def test_unchanged_reingest_is_current(conn, repo, caplog):
    name = register(conn, repo)
    first = indexing_ingest.ingest(conn, name, ENV)
    assert (first.mode, first.note) == ("full", None) and revision(conn, name) == (head(repo), False)  # FR-001
    rows = stored(conn, name)
    with caplog.at_level(logging.INFO, logger="golestan_code_mcp.ingest"):
        second = indexing_ingest.ingest(conn, name, ENV)
    assert second.mode == "current" and (second.files, second.symbols) == (0, 0)  # FR-002
    assert (second.added, second.changed, second.removed, second.unchanged) == (0, 0, 0, first.files)
    assert stored(conn, name) == rows
    record = json.loads(caplog.records[-1].getMessage())
    assert record["mode"] == "current" and record["unchanged"] == first.files  # FR-012


def test_failed_ingest_keeps_previous_index(conn, repo, monkeypatch):
    name = register(conn, repo)
    indexing_ingest.ingest(conn, name, ENV)
    before = stored(conn, name)
    (repo / "extra.py").write_text("def extra():\n    pass\n")

    def boom(cur, rows):
        raise RuntimeError("database went away")

    monkeypatch.setattr(indexing_write, "_insert_symbols", boom)
    with pytest.raises(RuntimeError):
        indexing_ingest.ingest(conn, name, ENV)
    assert stored(conn, name) == before
    assert revision(conn, name) == (head(repo), False)  # FR-007, SC-006


def test_every_symbol_gets_search_text(conn, repo):
    name = register(conn, repo)
    summary = indexing_ingest.ingest(conn, name, ENV)
    with conn.cursor() as cur:
        cur.execute(
            """select s.kind, s.name, f.path, s.source, s.search_text
                 from ccctx_symbols s join ccctx_files f on f.id = s.file_id join ccctx_repos r on r.id = f.repo_id
                where r.name = :n""",
            n=name,
        )
        rows = [tuple(v.read() if hasattr(v, "read") else v for v in row) for row in cur]
    assert len(rows) == summary.symbols
    for kind, symbol, path, source, text in rows:
        assert text == f"{kind} {symbol} in {path}\n{source}"


def test_ingested_symbols_are_searchable_at_once(conn, repo):
    name = register(conn, repo)
    indexing_ingest.ingest(conn, name, ENV)
    # no sleep, no sync call: the hybrid index syncs on commit (FR-014)
    assert query.search(conn, "helper", [name], mode="text")[0].name == "helper"
    assert "Service.run" in [r.name for r in query.search(conn, "method that runs the service", [name])]


def test_missing_model_changes_nothing(conn, repo, monkeypatch):
    name = register(conn, repo)
    indexing_ingest.ingest(conn, name, ENV)
    before = stored(conn, name)

    def missing(conn):
        raise model.ModelError("embedding model ALL_MINILM_L12_V2 is not set up; run `ccctx model load`")

    def no_discovery(*args):
        raise AssertionError("discover ran before the model check")

    monkeypatch.setattr(model, "require_model", missing)
    monkeypatch.setattr(indexing_files, "discover", no_discovery)
    with pytest.raises(model.ModelError, match="ccctx model load"):
        indexing_ingest.ingest(conn, name, ENV)
    assert stored(conn, name) == before  # FR-008


def test_dirty_tree_flagged(conn, repo):
    name = register(conn, repo)
    (repo / "untracked.py").write_text("x = 1\n")
    assert not indexing_ingest.ingest(conn, name, ENV).dirty
    (repo / "app.py").write_text(APP_PY + "\n# edited\n")
    assert indexing_ingest.ingest(conn, name, ENV).dirty


def test_refuses_non_git_and_empty_repos(conn, tmp_path):
    plain = tmp_path / "plain"
    plain.mkdir()
    with pytest.raises(IngestError, match="not a git repository"):
        indexing_ingest.ingest(conn, register(conn, plain), ENV)
    fresh = tmp_path / "fresh"
    fresh.mkdir()
    git(fresh, "init", "-q")
    with pytest.raises(IngestError, match="no commits"):
        indexing_ingest.ingest(conn, register(conn, fresh), ENV)


def test_concurrent_ingest_refused(conn, repo):
    name = register(conn, repo)
    other = db.connect(load())
    try:
        with other.cursor() as cur:
            cur.execute("select id from ccctx_repos where name = :n for update", n=name)
            with pytest.raises(IngestError, match="another ingest"):
                indexing_ingest.ingest(conn, name, ENV)
    finally:
        other.rollback()
        other.close()
