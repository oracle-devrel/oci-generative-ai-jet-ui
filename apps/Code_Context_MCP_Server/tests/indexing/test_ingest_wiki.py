"""An ingest and the wiki: pages whose citations changed are marked stale and recompiled."""

import pytest

from golestan_code_mcp.indexing import ingest as indexing_ingest
from golestan_code_mcp.wiki import build as wiki_build
from golestan_code_mcp.wiki import compile
from golestan_code_mcp.wiki import read

from indexing.helpers import ENV, head, pages_of, pkg_module, register, revision, write
from support import git

pytestmark = pytest.mark.needs_model  # the shared `conn` then requires the embedding model


def test_editing_a_cited_function_marks_and_recompiles_its_page(conn, wiki_repo):
    name = register(conn, wiki_repo)
    old = indexing_ingest.ingest(conn, name, ENV).commit
    wiki_build.build(conn, name)
    write(wiki_repo / "pkg" / "a.py", pkg_module("a").replace("return 3", "return 33"))
    git(wiki_repo, "commit", "-q", "-am", "edit a3")
    s = indexing_ingest.ingest(conn, name, ENV)
    reason = f"a0 changed ({old[:12]} -> {s.commit[:12]})"  # every symbol of the file moves to the new commit
    assert s.wiki == wiki_build.Refresh([("pkg", reason)], 1, 0, 0, None)
    assert pages_of(conn, name) == {"pkg": ("fresh", reason)}
    citations = {c.name: c for c in read.read(conn, "pkg", name).citations}
    assert citations["a3"].recorded_commit == s.commit == citations["a3"].current_commit


def test_uncited_change_and_no_change_mark_nothing(conn, wiki_repo):
    name = register(conn, wiki_repo)
    indexing_ingest.ingest(conn, name, ENV)
    wiki_build.build(conn, name)
    write(wiki_repo / "other" / "x.py", "def lonely():\n    return 1\n")
    git(wiki_repo, "commit", "-q", "-am", "edit uncited")
    assert indexing_ingest.ingest(conn, name, ENV).wiki == wiki_build.Refresh([], 0, 0, 0, None)
    assert indexing_ingest.ingest(conn, name, ENV).wiki is None  # current: nothing written
    git(wiki_repo, "revert", "--no-edit", "HEAD")
    git(wiki_repo, "revert", "--no-edit", "HEAD")
    s = indexing_ingest.ingest(conn, name, ENV)  # a new revision with the same content
    assert s.mode == "incremental" and s.wiki == wiki_build.Refresh([], 0, 0, 0, None)
    assert pages_of(conn, name) == {"pkg": ("fresh", None)}


def test_full_reingest_marks_and_recompiles_every_page(conn, wiki_repo):
    name = register(conn, wiki_repo)
    indexing_ingest.ingest(conn, name, ENV)
    wiki_build.build(conn, name)
    s = indexing_ingest.ingest(conn, name, ENV, full=True)
    assert s.wiki == wiki_build.Refresh([("pkg", "a0 was re-indexed")], 1, 0, 0, None)
    assert pages_of(conn, name) == {"pkg": ("fresh", "a0 was re-indexed")}
    assert all(c.path for c in read.read(conn, "pkg", name).citations)


def test_without_a_wiki_nothing_is_created(conn, wiki_repo):
    name = register(conn, wiki_repo)
    indexing_ingest.ingest(conn, name, ENV)
    write(wiki_repo / "pkg" / "a.py", pkg_module("a").replace("return 3", "return 33"))
    git(wiki_repo, "commit", "-q", "-am", "edit")
    assert indexing_ingest.ingest(conn, name, ENV).wiki is None
    assert pages_of(conn, name) == {}


def test_failed_recompile_keeps_the_ingestion(conn, wiki_repo, monkeypatch):
    name = register(conn, wiki_repo)
    indexing_ingest.ingest(conn, name, ENV)
    wiki_build.build(conn, name)
    write(wiki_repo / "pkg" / "b.py", pkg_module("b").replace("return 1", "return 11"))
    git(wiki_repo, "commit", "-q", "-am", "edit b1")

    def boom(*args, **kwargs):
        raise RuntimeError("compiler broke")

    monkeypatch.setattr(compile, "_compile", boom)
    s = indexing_ingest.ingest(conn, name, ENV)
    assert s.wiki.stale and s.wiki.stale[0][1].startswith("b0 changed") and s.wiki.recompiled == 0
    assert "compiler broke" in s.wiki.error
    assert revision(conn, name) == (head(wiki_repo), False)  # the ingestion is committed
    assert pages_of(conn, name)["pkg"][0] == "stale"
