"""The wiki's tables: pages and citations, their checks, keys and cascades."""

import oracledb
import pytest

from schema.helpers import add_citation, add_file, add_page, add_symbol, columns_of


def test_module_wiki_columns_and_tables(conn):
    with conn.cursor() as cur:
        cur.execute("select name from ccctx_migrations where version = 7")
        assert cur.fetchone() == ("module wiki",)
        assert columns_of(cur, "CCCTX_FILES")["DOC"] == ("VARCHAR2", "Y", 1000)
        assert columns_of(cur, "CCCTX_SYMBOLS")["DOC"] == ("VARCHAR2", "Y", 1000)
        wiki_at = columns_of(cur, "CCCTX_REPOS")["WIKI_AT"]
        assert wiki_at[0] == "TIMESTAMP(6) WITH TIME ZONE" and wiki_at[1] == "Y"
        pages = columns_of(cur, "CCCTX_WIKI_PAGES")
        assert {c: v[1] for c, v in pages.items()} == {
            "ID": "N", "REPO_ID": "N", "DIRECTORY": "N", "NAME": "N", "LANGUAGE": "N", "SYMBOLS": "N", "TEXT": "N",
            "SEARCH_TEXT": "N", "STATE": "N", "COMPILED_AT": "N", "COMPILER": "N", "STALE_REASON": "Y",
        }
        assert pages["TEXT"][0] == pages["SEARCH_TEXT"][0] == "CLOB"
        assert pages["COMPILED_AT"][0] == "TIMESTAMP(6) WITH TIME ZONE"
        citations = columns_of(cur, "CCCTX_WIKI_CITATIONS")
        assert {c: v[1] for c, v in citations.items()} == {
            "ID": "N", "PAGE_ID": "N", "SYMBOL_ID": "Y", "FILE_ID": "Y", "ROLE": "N", "NAME": "N", "KIND": "N",
            "COMMIT_SHA": "N", "CONTENT_HASH": "N",
        }
        cur.execute("select column_name from user_ind_columns where table_name = 'CCCTX_WIKI_CITATIONS'"
                    " and column_position = 1")
        assert {"PAGE_ID", "SYMBOL_ID", "FILE_ID"} <= {row[0] for row in cur}


def test_wiki_page_accepts_good_row(conn, repo_id):
    with conn.cursor() as cur:
        file_id = add_file(cur, repo_id)
        page_id = add_page(cur, repo_id, state="stale")
        add_citation(cur, page_id, "key", symbol_id=add_symbol(cur, file_id))
        add_citation(cur, page_id, "calls", symbol_id=add_symbol(cur, file_id, start=4, end=5))
        for role in ("file", "depends", "uses"):
            add_citation(cur, page_id, role, file_id=file_id)
    conn.rollback()


@pytest.mark.parametrize(("change", "constraint"), [
    ({"state": "old"}, "CCCTX_WIKI_PAGES_STATE_CK"),
    ({"symbols": 9}, "CCCTX_WIKI_PAGES_SYMBOLS_CK"),
])
def test_wiki_page_rejects_bad_values(conn, repo_id, change, constraint):
    with conn.cursor() as cur, pytest.raises(oracledb.DatabaseError, match=constraint):
        add_page(cur, repo_id, **change)
    conn.rollback()


@pytest.mark.parametrize(("second", "constraint"), [
    ({"directory": "pkg", "name": "other"}, "CCCTX_WIKI_PAGES_DIR_UK"),
    ({"directory": "src/pkg", "name": "pkg"}, "CCCTX_WIKI_PAGES_NAME_UK"),
])
def test_wiki_page_directory_and_name_unique_per_repo(conn, repo_id, second, constraint):
    with conn.cursor() as cur:
        add_page(cur, repo_id, "pkg", "pkg")
        with pytest.raises(oracledb.IntegrityError, match=constraint):
            add_page(cur, repo_id, **second)
    conn.rollback()


def test_wiki_citation_rejects_bad_role_and_key_with_file(conn, repo_id):
    with conn.cursor() as cur:
        file_id = add_file(cur, repo_id)
        symbol_id = add_symbol(cur, file_id)
        page_id = add_page(cur, repo_id)
        cur.execute("select count(*) from user_constraints where constraint_name = 'CCCTX_WIKI_CITATIONS_ROLE_CK'")
        assert cur.fetchone()[0] == 1
        # an unknown role fails the target check too; which check Oracle reports first is not defined
        with pytest.raises(oracledb.DatabaseError, match="CCCTX_WIKI_CITATIONS_(ROLE|TARGET)_CK"):
            add_citation(cur, page_id, "owner", file_id=file_id)
        with pytest.raises(oracledb.DatabaseError, match="CCCTX_WIKI_CITATIONS_TARGET_CK"):
            add_citation(cur, page_id, "key", symbol_id=symbol_id, file_id=file_id)
        with pytest.raises(oracledb.DatabaseError, match="CCCTX_WIKI_CITATIONS_TARGET_CK"):
            add_citation(cur, page_id, "file", symbol_id=symbol_id, file_id=file_id)
    conn.rollback()


def test_wiki_citation_keys_set_null_on_delete(conn, repo_id):
    with conn.cursor() as cur:
        f1, f2 = add_file(cur, repo_id, "a.py"), add_file(cur, repo_id, "b.py")
        symbol_id = add_symbol(cur, f2)
        page_id = add_page(cur, repo_id)
        key = add_citation(cur, page_id, "key", symbol_id=symbol_id)
        file_cit = add_citation(cur, page_id, "file", file_id=f1)
        cur.execute("delete from ccctx_symbols where id = :i", i=symbol_id)
        cur.execute("delete from ccctx_files where id = :i", i=f1)
        rows = cur.execute("select id, symbol_id, file_id from ccctx_wiki_citations where page_id = :p order by id",
                           p=page_id).fetchall()
    conn.rollback()
    assert rows == sorted([(key, None, None), (file_cit, None, None)])


def test_wiki_page_and_repo_delete_cascade(conn, repo_id):
    with conn.cursor() as cur:
        file_id = add_file(cur, repo_id)
        page_id = add_page(cur, repo_id)
        add_citation(cur, page_id, "file", file_id=file_id)
        cur.execute("delete from ccctx_wiki_pages where id = :i", i=page_id)
        assert cur.execute("select count(*) from ccctx_wiki_citations where page_id = :p", p=page_id).fetchone()[0] == 0
        page_id = add_page(cur, repo_id)
        add_citation(cur, page_id, "file", file_id=file_id)
        cur.execute("delete from ccctx_repos where id = :i", i=repo_id)
        assert cur.execute("select count(*) from ccctx_wiki_pages where repo_id = :r", r=repo_id).fetchone()[0] == 0
        assert cur.execute("select count(*) from ccctx_wiki_citations where page_id = :p", p=page_id).fetchone()[0] == 0
    conn.rollback()
