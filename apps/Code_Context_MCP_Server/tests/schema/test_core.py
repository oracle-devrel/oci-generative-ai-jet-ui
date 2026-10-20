"""The core tables: migrations, repositories, files, symbols, revisions and the language columns."""

import uuid

import oracledb
import pytest

from golestan_code_mcp import schema

from schema.helpers import SHA, TABLES, add_file, add_symbol, columns_of, counts, insert


def test_tables_exist_and_version_recorded(conn):
    with conn.cursor() as cur:
        cur.execute("select table_name from user_tables")
        assert TABLES <= {row[0] for row in cur}
        cur.execute("select version, name from ccctx_migrations order by version")
        assert cur.fetchall()[:4] == [
            (1, "core tables"), (2, "symbol commit"), (3, "symbol embedding"), (4, "hybrid search text")
        ]
        cur.execute("select column_name, data_type, nullable from user_tab_columns where table_name = 'CCCTX_SYMBOLS'")
        columns = {name: (kind, nullable) for name, kind, nullable in cur}
        assert "COMMIT_SHA" in columns
        assert columns["SEARCH_TEXT"] == ("CLOB", "Y")
        assert "EMBEDDING" not in columns  # replaced by the hybrid index's own vectors
        cur.execute("select count(*) from user_indexes where index_name = 'CCCTX_SYMBOLS_EMBEDDING_IX'")
        assert cur.fetchone()[0] == 0
        cur.execute("select table_name from user_tables where table_name = 'CCCTX_EMBEDDING_MODEL'")
        assert cur.fetchone()


def test_migrate_three_times_changes_nothing(conn):
    before = counts(conn)
    for _ in range(3):
        assert schema.migrate(conn) == []
        assert counts(conn) == before


@pytest.mark.parametrize("name", ["Flask", "a b", "a/b", "x" * 65])
def test_bad_repo_name_rejected(conn, name):
    with conn.cursor() as cur, pytest.raises(oracledb.DatabaseError):
        cur.execute("insert into ccctx_repos (name, path) values (:n, :p)", n=name, p=f"/tmp/bad-{uuid.uuid4().hex}")
    conn.rollback()


def test_file_path_unique_per_repo(conn, repo_id):
    with conn.cursor() as cur:
        add_file(cur, repo_id)
        with pytest.raises(oracledb.IntegrityError):
            add_file(cur, repo_id)
    conn.rollback()


@pytest.mark.parametrize(("kind", "start", "end"), [("lambda", 1, 2), ("function", 5, 4), ("function", 0, 1)])
def test_bad_symbol_rejected(conn, repo_id, kind, start, end):
    with conn.cursor() as cur:
        file_id = add_file(cur, repo_id)
        with pytest.raises(oracledb.DatabaseError):
            add_symbol(cur, file_id, kind, start, end)
    conn.rollback()


def test_delete_cascades(conn, repo_id):
    with conn.cursor() as cur:
        file_id = add_file(cur, repo_id)
        add_symbol(cur, file_id, "class")
        cur.execute("delete from ccctx_repos where id = :i", i=repo_id)
        cur.execute("select count(*) from ccctx_files where repo_id = :i", i=repo_id)
        assert cur.fetchone()[0] == 0
        cur.execute("select count(*) from ccctx_symbols where file_id = :i", i=file_id)
        assert cur.fetchone()[0] == 0
    conn.rollback()


@pytest.mark.parametrize("sha", ["a" * 40, "0123456789abcdef" * 4])
def test_commit_sha_accepts_sha1_and_sha256(conn, repo_id, sha):
    with conn.cursor() as cur:
        add_symbol(cur, add_file(cur, repo_id), sha=sha)
    conn.rollback()


@pytest.mark.parametrize("sha", ["abc", "A" * 40, "g" * 40, "a" * 41, None])
def test_commit_sha_rejects_bad_values(conn, repo_id, sha):
    with conn.cursor() as cur:
        file_id = add_file(cur, repo_id)
        with pytest.raises(oracledb.DatabaseError):
            add_symbol(cur, file_id, sha=sha)
    conn.rollback()


def test_backfill_fills_search_text(conn, repo_id):
    with conn.cursor() as cur:
        symbol_id = add_symbol(cur, add_file(cur, repo_id, "pkg/mod.py"), "method", 3, 9)
        cur.execute(schema.BACKFILL_SEARCH_TEXT)
        text = cur.execute("select search_text from ccctx_symbols where id = :i", i=symbol_id).fetchone()[0].read()
    conn.rollback()
    assert text == "method f in pkg/mod.py\ndef f(): pass"


def test_repo_indexed_revision_columns(conn):
    with conn.cursor() as cur:
        cur.execute("select name from ccctx_migrations where version = 5")
        assert cur.fetchone() == ("repo indexed revision",)
        cur.execute("select column_name, data_type, nullable from user_tab_columns where table_name = 'CCCTX_REPOS'")
        columns = {name: (kind, nullable) for name, kind, nullable in cur}
    assert columns["INDEXED_COMMIT"] == ("VARCHAR2", "Y")
    assert columns["INDEXED_DIRTY"] == ("BOOLEAN", "Y")
    assert columns["INDEXED_AT"][1] == "Y" and columns["INDEXED_AT"][0].startswith("TIMESTAMP")


@pytest.mark.parametrize("sha", [None, "a" * 40, "0123456789abcdef" * 4])
def test_indexed_commit_accepts_null_sha1_sha256(conn, repo_id, sha):
    with conn.cursor() as cur:
        cur.execute("update ccctx_repos set indexed_commit = :c where id = :i", c=sha, i=repo_id)
    conn.rollback()


@pytest.mark.parametrize("sha", ["abc", "A" * 40, "g" * 40, "a" * 41])
def test_indexed_commit_rejects_bad_values(conn, repo_id, sha):
    with conn.cursor() as cur, pytest.raises(oracledb.DatabaseError):
        cur.execute("update ccctx_repos set indexed_commit = :c where id = :i", c=sha, i=repo_id)
    conn.rollback()


# --- language coverage (specs/012-language-coverage/data-model.md) ---


def test_language_coverage_columns(conn):
    with conn.cursor() as cur:
        assert cur.execute("select name from ccctx_migrations where version = 10").fetchone() == ("language coverage",)
        assert columns_of(cur, "CCCTX_FILES")["NAMESPACES"][:2] == ("JSON", "Y")
        assert columns_of(cur, "CCCTX_SYMBOLS")["EXPORTED"][:2] == ("BOOLEAN", "Y")


def test_exported_backfill_follows_the_name_rule(conn, repo_id):
    with conn.cursor() as cur:
        go = insert(cur, "insert into ccctx_files (repo_id, path, language, content_hash) values (:r, 'a.go', 'go', :h)",
                    r=repo_id, h="0" * 64)
        py = add_file(cur, repo_id, "b.py")
        rows = {}
        for fid, name, kind in [(go, "Serve", "function"), (go, "Server.close", "method"), (py, "Flask._private",
                                "method"), (py, "url_for", "function"), (py, "b.py:1-60", "chunk")]:
            rows[name] = insert(cur, "insert into ccctx_symbols (file_id, name, kind, start_line, end_line, source,"
                                     " content_hash, commit_sha) values (:f, :n, :k, 1, 2, 'x', :h, :c)",
                                f=fid, n=name, k=kind, h="0" * 64, c=SHA)
        update = next(s for v, n, steps in schema.MIGRATIONS if v == 10 for s in steps
                      if isinstance(s, str) and s.lstrip().startswith("update"))
        cur.execute(update)
        got = {n: cur.execute("select exported from ccctx_symbols where id = :i", i=i).fetchone()[0]
               for n, i in rows.items()}
        assert got == {"Serve": True, "Server.close": False, "Flask._private": False, "url_for": True,
                       "b.py:1-60": None}
        cur.execute("update ccctx_symbols set exported = true where id = :i", i=rows["Flask._private"])
        cur.execute(update)  # only null rows are touched
        assert cur.execute("select exported from ccctx_symbols where id = :i",
                           i=rows["Flask._private"]).fetchone()[0] is True
    conn.rollback()


def test_schema_version_is_ten(conn):
    assert schema.version(conn) == 10
