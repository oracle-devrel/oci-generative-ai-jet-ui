"""What an ingest extracts besides symbols: graph edges, docs, visibility and namespaces, and re-reading files
stored under older extraction rules.
"""

import json
import logging
import uuid
from collections import Counter

import pytest

from golestan_code_mcp import registry
from golestan_code_mcp.indexing import ingest as indexing_ingest
from golestan_code_mcp.indexing import write as indexing_write
from golestan_code_mcp.graph import build
from golestan_code_mcp.memory import consolidate
from golestan_code_mcp.memory import recall
from golestan_code_mcp.memory import runs
from golestan_code_mcp.memory import store
from golestan_code_mcp.search import feedback as search_feedback

from indexing.helpers import (DOC_GO, DOC_PY, ENV, LIB_PY, USE_PY, assert_matches_full, callers_of, docs,
    extract_version, forget_graph, named_ids, register, relations, stored, symbol_ids, visibility, write)
from support import git

pytestmark = pytest.mark.needs_model  # the shared `conn` then requires the embedding model


def test_graph_follows_edits_and_deletions(conn, graph_repo):
    name = register(conn, graph_repo)
    indexing_ingest.ingest(conn, name, ENV)
    assert callers_of(conn, name, "target") == {"caller", "other", "(module)"}
    assert callers_of(conn, name, "helper") == {"Service.run"}

    write(graph_repo / "lib.py", LIB_PY.replace("return 1", "return 2"))  # the callee gets a new id
    git(graph_repo, "commit", "-q", "-am", "edit callee")
    s = indexing_ingest.ingest(conn, name, ENV)
    assert (s.mode, s.changed) == ("incremental", 1)
    assert callers_of(conn, name, "target") == {"caller", "other", "(module)"}  # US4 scenario 2: use.py not re-read

    write(graph_repo / "use.py", USE_PY.replace("def other():\n    return target()\n\n\n", ""))
    git(graph_repo, "commit", "-q", "-am", "drop a caller")
    indexing_ingest.ingest(conn, name, ENV)
    assert callers_of(conn, name, "target") == {"caller", "(module)"}  # US4 scenario 1
    assert any("'use.py', 'lib.py'" in row for row in relations(conn, name)["imports"])
    assert_matches_full(conn, name)


def test_repository_indexed_before_the_graph_is_reread_without_reembedding(conn, graph_repo):
    name = register(conn, graph_repo)
    first = indexing_ingest.ingest(conn, name, ENV)
    full_graph = relations(conn, name)
    ids = {path: named_ids(conn, name, path) for path in ("app.py", "lib.py", "use.py")}
    forget_graph(conn, name)
    assert callers_of(conn, name, "target") == set()

    s = indexing_ingest.ingest(conn, name, ENV)  # FR-013: same revision, yet every file is re-read for its refs
    assert s.mode == "incremental" and (s.changed, s.files) == (first.files, first.files)
    assert s.symbols == 0  # no symbol changed, so nothing is re-embedded
    assert {path: named_ids(conn, name, path) for path in ids} == ids
    assert extract_version(conn, name) == indexing_write.EXTRACT_VERSION
    assert relations(conn, name) == full_graph
    assert indexing_ingest.ingest(conn, name, ENV).mode == "current"


def test_failed_reread_keeps_the_old_extract_version(conn, graph_repo, monkeypatch):
    name = register(conn, graph_repo)
    indexing_ingest.ingest(conn, name, ENV)
    forget_graph(conn, name)

    def boom(cur, repo_id):
        raise RuntimeError("database went away")

    monkeypatch.setattr(build, "rebuild", boom)
    with pytest.raises(RuntimeError):
        indexing_ingest.ingest(conn, name, ENV)
    assert extract_version(conn, name) is None and relations(conn, name)["call refs"] == []


def test_docs_are_stored_and_follow_edits(conn, repo):
    write(repo / "doc.py", DOC_PY)
    write(repo / "run.go", DOC_GO)
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "docs")
    name = register(conn, repo)
    indexing_ingest.ingest(conn, name, ENV)
    files, symbols = docs(conn, name)
    assert files["doc.py"] == "Module doc." and files["run.go"] is None and files["notes.txt"] is None
    assert symbols["documented"][0] == "Does a thing." and symbols["Run"][0] == "Run runs."
    assert symbols["helper"][0] is None and symbols["notes.txt:1-60"][0] is None

    write(repo / "doc.py", DOC_PY.replace("Module doc.", "Edited module doc."))
    write(repo / "run.go", DOC_GO.replace("// Run runs.", "// Run runs fast."))
    git(repo, "commit", "-q", "-am", "edit docs")
    indexing_ingest.ingest(conn, name, ENV)
    files, after = docs(conn, name)
    assert files["doc.py"] == "Edited module doc."
    assert after["Run"] == ("Run runs fast.", symbols["Run"][1])  # kept row, new doc
    assert_matches_full(conn, name)


def test_extract_version_1_is_reread_once_without_new_symbols(conn, repo):
    write(repo / "doc.py", DOC_PY)
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "docs")
    name = register(conn, repo)
    first = indexing_ingest.ingest(conn, name, ENV)
    ids = {path: named_ids(conn, name, path) for path in ("app.py", "doc.py")}
    with conn.cursor() as cur:
        rid = registry.repo_id(conn, name)
        cur.execute("update ccctx_repos set extract_version = 1 where id = :r", r=rid)
        cur.execute("update ccctx_files set doc = null where repo_id = :r", r=rid)
        cur.execute("update ccctx_symbols set doc = null where file_id in (select id from ccctx_files where repo_id = :r)",
                    r=rid)
    conn.commit()
    assert indexing_write.EXTRACT_VERSION > 1
    s = indexing_ingest.ingest(conn, name, ENV)
    assert s.mode == "incremental" and s.changed == first.files and s.symbols == 0
    assert {path: named_ids(conn, name, path) for path in ids} == ids
    files, symbols = docs(conn, name)
    assert files["doc.py"] == "Module doc." and symbols["documented"][0] == "Does a thing."
    assert extract_version(conn, name) == indexing_write.EXTRACT_VERSION and indexing_ingest.ingest(conn, name, ENV).mode == "current"


def test_exported_and_namespaces_are_stored_and_stable(conn, repo):
    name = register(conn, repo)
    indexing_ingest.ingest(conn, name, ENV)
    rows = visibility(conn, name)
    assert {namespaces for _, _, namespaces, *_ in rows} == {None}
    for path, language, _, symbol, kind, exported in rows:
        if kind == "chunk" or symbol is None:
            assert exported is None, (path, symbol)
        else:
            last = symbol.rpartition(".")[2]
            assert exported == (last[:1].isupper() if language == "go" else not last.startswith("_")), symbol
    assert any(exported is True for *_, exported in rows)
    indexing_ingest.ingest(conn, name, ENV, full=True)
    assert visibility(conn, name) == rows


def test_files_whose_language_gained_rules_are_re_read(conn, before_csharp, caplog):
    name, _ = before_csharp
    python_ids = symbol_ids(conn, name, "app.py")
    with caplog.at_level(logging.INFO, logger="golestan_code_mcp.ingest"):
        summary = indexing_ingest.ingest(conn, name, ENV)
    assert summary.mode == "incremental" and summary.reparsed == Counter(csharp=1)
    assert (summary.changed, summary.added, summary.removed, summary.files) == (1, 0, 0, 1)
    assert {(r[1], r[3], r[4]) for r in stored(conn, name) if r[0] == "shop/Cart.cs"} == {
        ("csharp", "Cart", "class"), ("csharp", "Cart.Total", "method")}
    assert symbol_ids(conn, name, "app.py") == python_ids  # unchanged files of other languages are not read
    record = next(json.loads(r.getMessage()) for r in caplog.records if '"event": "ingest"' in r.getMessage())
    assert record["reparsed"] == {"csharp": 1}
    assert indexing_ingest.ingest(conn, name, ENV).mode == "current"
    assert indexing_ingest.ingest(conn, name, ENV, full=True).reparsed == Counter()


def test_uses_and_facts_of_the_old_windows_end_like_removed_code(conn, before_csharp):
    name, _ = before_csharp
    window = next(r[3] for r in stored(conn, name) if r[0] == "shop/Cart.cs")
    with conn.cursor() as cur:
        search_feedback.write_use(cur, {"repo_id": registry.repo_id(conn, name), "path": "shop/Cart.cs", "name": window,
                                 "kind": "chunk", "how": "cited", "client": "t", "session": uuid.uuid4().hex,
                                 "run_id": None})
    conn.commit()
    run = {"tool": "search_code", "arguments": {"query": "cart total", "repo": name}, "question": "cart total",
           "client": None, "status": "ok", "reason": None, "ms": 1, "result_count": 1, "repos": [name],
           "results": [{"kind": "chunk", "repo": name, "name": window, "path": "shop/Cart.cs", "start_line": 1,
                        "end_line": 10}]}
    runs.store_runs(conn, [run])
    try:
        consolidate.consolidate(conn, name, ENV)
        assert [(f.subject, f.state) for f in recall.facts(conn, name)] == [(window, "fresh")]
        indexing_ingest.ingest(conn, name, ENV)  # the window is gone: the file is definitions now
        assert [(f.subject, f.state) for f in recall.facts(conn, name)] == [(window, "stale")]
        assert [(r.name, r.indexed) for r in search_feedback.listing(conn, name)] == [(window, False)]
    finally:
        store.client(conn).delete_user(name, cascade=True)
