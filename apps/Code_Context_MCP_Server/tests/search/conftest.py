"""Fixtures of the search tests: throwaway repositories and pages, and a repository for usage feedback."""

import pytest
import oracledb

from golestan_code_mcp.parsing import chunks

from search.feedback_helpers import FILES, make_repo
from search.helpers import A, B, C, D, LEDGER_SYMBOLS, LEDGER_TEXT, SYMBOLS, add_symbol


@pytest.fixture(scope="module")
def repos(conn):
    """Three throwaway repositories whose symbols the hybrid index picks up on commit."""
    with conn.cursor() as cur:
        for repo, symbols in SYMBOLS.items():
            rid = cur.var(int)
            cur.execute("insert into ccctx_repos (name, path) values (:n, :p) returning id into :i",
                        n=repo, p=f"/tmp/{repo}", i=rid)
            for name, kind, path, source in symbols:
                fid = cur.var(int)
                cur.execute("insert into ccctx_files (repo_id, path, language, content_hash)"
                            " values (:r, :p, :l, :h) returning id into :i",
                            r=rid.getvalue()[0], p=path, l=chunks.detect_language(path), h="0" * 64, i=fid)
                add_symbol(cur, fid.getvalue()[0], name, kind, path, source)
    conn.commit()
    return A, B, C


@pytest.fixture(scope="module")
def ledger(conn, repos):
    """Repository D: two Python symbols and a wiki page about its ledger package, in the page index."""
    from golestan_code_mcp.wiki import store

    with conn.cursor() as cur:
        assert store.ensure_index(cur)
        rid = cur.var(int)
        cur.execute("insert into ccctx_repos (name, path) values (:n, :p) returning id into :i",
                    n=D, p=f"/tmp/{D}", i=rid)
        for name, source in LEDGER_SYMBOLS:
            fid = cur.var(int)
            cur.execute("insert into ccctx_files (repo_id, path, language, content_hash)"
                        " values (:r, :p, 'python', :h) returning id into :i",
                        r=rid.getvalue()[0], p=f"src/ledger/{name}.py", h="0" * 64, i=fid)
            add_symbol(cur, fid.getvalue()[0], name, "function", f"src/ledger/{name}.py", source)
        cur.setinputsizes(t=oracledb.DB_TYPE_CLOB, s=oracledb.DB_TYPE_CLOB)
        cur.execute(
            """insert into ccctx_wiki_pages (repo_id, directory, name, language, symbols, text, search_text, state,
                                             compiled_at, compiler)
               values (:r, 'src/ledger', 'ledger', 'python', 10, :t, :s, 'fresh', systimestamp, 'ccctx-wiki/1')""",
            r=rid.getvalue()[0], t=LEDGER_TEXT, s=f"page ledger in src/ledger\n{LEDGER_TEXT}")
    conn.commit()
    return D


@pytest.fixture(scope="module")
def fb(conn, tmp_path_factory):
    repo = make_repo(conn, tmp_path_factory.mktemp("fb") / "repo", FILES)
    yield repo
    with conn.cursor() as cur:
        cur.execute("delete from ccctx_repos where id = :i", i=repo.id)  # its uses go with it
    conn.commit()


@pytest.fixture
def clean(conn, fb):
    """The fixture repository with no uses, before and after the test."""
    def wipe():
        with conn.cursor() as cur:
            cur.execute("delete from ccctx_feedback where repo_id = :r", r=fb.id)
        conn.commit()
    wipe()
    yield fb
    wipe()
