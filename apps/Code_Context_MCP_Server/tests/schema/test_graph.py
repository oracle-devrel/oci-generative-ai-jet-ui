"""The code graph's tables: call and import refs, edges, and the property graph."""

import oracledb
import pytest

from schema.helpers import GRAPH_TABLES, add_file, add_symbol


def test_code_graph_tables_and_extract_version(conn):
    with conn.cursor() as cur:
        cur.execute("select name from ccctx_migrations where version = 6")
        assert cur.fetchone() == ("code graph",)
        cur.execute("select table_name from user_tables")
        assert GRAPH_TABLES <= {row[0] for row in cur}
        cur.execute("select data_type, nullable from user_tab_columns"
                    " where table_name = 'CCCTX_REPOS' and column_name = 'EXTRACT_VERSION'")
        assert cur.fetchone() == ("NUMBER", "Y")


def test_call_ref_form_rejects_other_values(conn, repo_id):
    with conn.cursor() as cur:
        file_id = add_file(cur, repo_id)
        for form in ("bare", "attr"):
            cur.execute("insert into ccctx_call_refs (file_id, name, form, line) values (:f, 'g', :m, 1)", f=file_id, m=form)
        with pytest.raises(oracledb.DatabaseError, match="CCCTX_CALL_REFS_FORM_CK"):
            cur.execute("insert into ccctx_call_refs (file_id, name, form, line) values (:f, 'g', 'call', 1)", f=file_id)
    conn.rollback()


def test_import_pair_unique(conn, repo_id):
    with conn.cursor() as cur:
        a, b = add_file(cur, repo_id, "a.py"), add_file(cur, repo_id, "b.py")
        cur.execute("insert into ccctx_imports (importer_id, imported_id) values (:a, :b)", a=a, b=b)
        cur.execute("insert into ccctx_imports (importer_id, imported_id) values (:b, :a)", a=a, b=b)  # reverse is a new pair
        with pytest.raises(oracledb.IntegrityError, match="CCCTX_IMPORTS_PAIR_UK"):
            cur.execute("insert into ccctx_imports (importer_id, imported_id) values (:a, :b)", a=a, b=b)
    conn.rollback()


def test_file_delete_cascades_refs_and_edges(conn, repo_id):
    with conn.cursor() as cur:
        f1, f2 = add_file(cur, repo_id, "a.py"), add_file(cur, repo_id, "b.py")
        s1, s3 = add_symbol(cur, f1), add_symbol(cur, f2)
        cur.execute("insert into ccctx_call_refs (file_id, caller_id, name, form, receiver, line)"
                    " values (:f, :s, 'g', 'attr', 'self', 2)", f=f1, s=s1)
        cur.execute("insert into ccctx_import_refs (file_id, module, rel_level, bound) values (:f, 'b', 1, 'b')", f=f1)
        for caller, callee in ((s1, s3), (s3, s1)):
            cur.execute("insert into ccctx_calls (caller_id, callee_id, line) values (:a, :b, 1)", a=caller, b=callee)
        for file_id, callee in ((f1, s3), (f2, s1)):
            cur.execute("insert into ccctx_file_calls (file_id, callee_id, line) values (:f, :s, 1)", f=file_id, s=callee)
        for a, b in ((f1, f2), (f2, f1)):
            cur.execute("insert into ccctx_imports (importer_id, imported_id) values (:a, :b)", a=a, b=b)
        cur.execute("delete from ccctx_files where id = :i", i=f1)
        left = {
            table: cur.execute(f"select count(*) from {table} where {where}", ids).fetchone()[0]
            for table, where, ids in (
                ("ccctx_symbols", "id = :s", {"s": s1}),
                ("ccctx_call_refs", "file_id = :f", {"f": f1}),
                ("ccctx_import_refs", "file_id = :f", {"f": f1}),
                ("ccctx_calls", "caller_id = :s or callee_id = :s", {"s": s1}),
                ("ccctx_file_calls", "file_id = :f or callee_id = :s", {"f": f1, "s": s1}),
                ("ccctx_imports", "importer_id = :f or imported_id = :f", {"f": f1}),
            )
        }
        assert left == dict.fromkeys(left, 0)
        cur.execute("select count(*) from ccctx_symbols where id = :s", s=s3)
        assert cur.fetchone()[0] == 1  # the other file's symbol survives
    conn.rollback()


def test_graph_one_hop_calls(conn, repo_id):
    with conn.cursor() as cur:
        cur.execute("select count(*) from user_property_graphs where graph_name = 'CCCTX_GRAPH'")
        assert cur.fetchone()[0] == 1
        file_id = add_file(cur, repo_id)
        caller, callee = add_symbol(cur, file_id, start=1, end=2), add_symbol(cur, file_id, start=4, end=5)
        cur.execute("insert into ccctx_calls (caller_id, callee_id, line) values (:a, :b, 2)", a=caller, b=callee)
        rows = cur.execute(
            "select caller_id, line, callee_id from graph_table (ccctx_graph"
            " match (c is symbol) -[e is calls]-> (t is symbol) where t.id = :t"
            " columns (c.id as caller_id, e.line as line, t.id as callee_id))", t=callee,
        ).fetchall()
    conn.rollback()
    assert rows == [(caller, 2, callee)]
