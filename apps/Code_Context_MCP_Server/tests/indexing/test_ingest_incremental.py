"""An incremental ingest: only what changed since the last run is re-read, and the result matches a full one."""

import pytest

from golestan_code_mcp.indexing import ingest as indexing_ingest
from golestan_code_mcp.search import query

from indexing.helpers import (APP_PY, ENV, MAIN_GO, assert_matches_full, head, named_ids, register, revision, stored,
    symbol_ids, write)
from support import git

pytestmark = pytest.mark.needs_model  # the shared `conn` then requires the embedding model


def test_uncommitted_edit_at_same_head_is_indexed(conn, repo):
    name = register(conn, repo)
    indexing_ingest.ingest(conn, name, ENV)
    write(repo / "app.py", APP_PY + "\n\ndef extra():\n    pass\n")
    s = indexing_ingest.ingest(conn, name, ENV)
    assert (s.mode, s.added, s.changed, s.removed) == ("incremental", 0, 1, 0) and s.dirty
    assert revision(conn, name) == (head(repo), True)
    assert "extra" in {r[3] for r in stored(conn, name)}
    git(repo, "checkout", "--", "app.py")  # back to the commit: only the dirty flag reveals the stale rows
    s = indexing_ingest.ingest(conn, name, ENV)
    assert (s.mode, s.changed) == ("incremental", 1) and revision(conn, name) == (head(repo), False)
    assert "extra" not in {r[3] for r in stored(conn, name)}
    assert_matches_full(conn, name)


def test_only_changed_files_are_reprocessed(conn, repo):
    name = register(conn, repo)
    first = indexing_ingest.ingest(conn, name, ENV)
    kept = symbol_ids(conn, name, "app.py")
    main_id = symbol_ids(conn, name, "main.go")
    write(repo / "main.go", MAIN_GO + "\nfunc other() {\n}\n")
    (repo / "lib").mkdir()
    git(repo, "mv", "web.js", "lib/web.js")
    git(repo, "rm", "-q", "notes.txt")
    write(repo / "new.py", "def fresh():\n    pass\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "change")
    write(repo / "extra.py", "def untracked():\n    pass\n")

    s = indexing_ingest.ingest(conn, name, ENV)
    assert s.mode == "incremental" and s.commit == head(repo) and not s.dirty
    assert (s.added, s.changed, s.removed, s.unchanged) == (3, 1, 2, 4)  # FR-008
    rewritten = {"main.go", "lib/web.js", "new.py", "extra.py"}
    # main.go's untouched `main` keeps its row; only its new `other` is inserted and embedded
    assert s.files == 4 and s.symbols == len([r for r in stored(conn, name) if r[0] in rewritten]) - 1
    assert main_id[0] in symbol_ids(conn, name, "main.go")
    paths = {r[0] for r in stored(conn, name)}
    assert rewritten <= paths and not {"web.js", "notes.txt"} & paths  # FR-005
    assert symbol_ids(conn, name, "app.py") == kept  # FR-004: unchanged rows are not rewritten
    assert {r[9] for r in stored(conn, name) if r[0] == "app.py"} == {first.commit}
    assert revision(conn, name) == (head(repo), False)
    assert_matches_full(conn, name)


def test_change_reverted_in_a_later_commit_is_unchanged(conn, repo):
    name = register(conn, repo)
    indexing_ingest.ingest(conn, name, ENV)
    write(repo / "app.py", "x = 1\n")
    git(repo, "commit", "-q", "-am", "edit")
    git(repo, "revert", "--no-edit", "HEAD")
    s = indexing_ingest.ingest(conn, name, ENV)
    assert (s.mode, s.added, s.changed, s.removed, s.unchanged) == ("incremental", 0, 0, 0, 7)
    assert revision(conn, name) == (head(repo), False)  # the revision moves even with nothing to re-index


def test_deleted_and_newly_skipped_files_leave_the_index(conn, repo):
    name = register(conn, repo)
    indexing_ingest.ingest(conn, name, ENV)
    (repo / "app.py").unlink()
    write(repo / "main.go", "x" * 3000)  # now too large
    (repo / "web.js").write_bytes(b"\x00binary")
    s = indexing_ingest.ingest(conn, name, ENV)
    assert (s.mode, s.added, s.changed, s.removed) == ("incremental", 0, 0, 3)
    assert not {"app.py", "main.go", "web.js"} & {r[0] for r in stored(conn, name)}  # FR-005, SC-003
    assert all(r.path != "app.py" for r in query.search(conn, "helper", [name], mode="text"))
    assert_matches_full(conn, name)


def test_full_rebuild_on_up_to_date_repository(conn, repo):
    name = register(conn, repo)
    first = indexing_ingest.ingest(conn, name, ENV)
    s = indexing_ingest.ingest(conn, name, ENV, full=True)  # FR-009, SC-004
    assert s.mode == "full" and s.note is None and (s.files, s.symbols) == (first.files, first.symbols)


@pytest.mark.parametrize(("recorded", "note"), [
    (None, "no recorded revision"), ("f" * 40, "is no longer in the repository"),
])
def test_unknown_revision_rebuilds_in_full(conn, repo, recorded, note):
    name = register(conn, repo)
    first = indexing_ingest.ingest(conn, name, ENV)
    with conn.cursor() as cur:
        cur.execute("update ccctx_repos set indexed_commit = :c where name = :n", c=recorded, n=name)
    conn.commit()
    s = indexing_ingest.ingest(conn, name, ENV)  # FR-010
    assert s.mode == "full" and note in s.note and s.symbols == first.symbols
    assert revision(conn, name) == (head(repo), False)


def test_edited_file_keeps_its_unchanged_symbols(conn, repo):
    name = register(conn, repo)
    indexing_ingest.ingest(conn, name, ENV)
    before = {r[3]: r for r in stored(conn, name) if r[0] == "app.py"}
    ids = named_ids(conn, name, "app.py")
    git(repo, "checkout", "-q", "-b", "edit")
    edited = APP_PY.replace("import os\n", "import os\nimport sys\n\n\ndef top():\n    pass\n")
    edited = edited.replace("return x + 1", "return x + 2")
    (repo / "app.py").write_text(edited, encoding="utf-8", newline="\n")
    git(repo, "commit", "-q", "-am", "edit")
    s = indexing_ingest.ingest(conn, name, ENV)
    after = {r[3]: r for r in stored(conn, name) if r[0] == "app.py"}
    assert s.symbols == 2  # `top` is new and `helper` changed; Service and Service.run only moved
    assert after["Service"][5:7] == (before["Service"][5] + 5, before["Service"][6] + 5)
    assert after["Service"][9] == head(repo)  # its lines were read at the new revision
    now = named_ids(conn, name, "app.py")
    assert (now["Service"], now["Service.run"]) == (ids["Service"], ids["Service.run"])
    assert now["helper"] != ids["helper"]
    assert_matches_full(conn, name)
