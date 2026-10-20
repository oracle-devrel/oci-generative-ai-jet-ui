"""The memory and feedback tables: runs, their repositories, the package's schema, and uses."""

import oracledb
import pytest

from schema.helpers import add_run, add_use, columns_of


def test_agent_memory_tables_and_package_schema(conn):
    with conn.cursor() as cur:
        cur.execute("select name from ccctx_migrations where version = 8")
        assert cur.fetchone() == ("agent memory",)
        runs = columns_of(cur, "CCCTX_MEMORY_RUNS")
        assert {c: v[1] for c, v in runs.items()} == {
            "ID": "N", "CALLED_AT": "N", "TOOL": "N", "ARGUMENTS": "N", "QUESTION": "Y", "CLIENT": "Y", "STATUS": "N",
            "REASON": "Y", "MS": "Y", "RESULT_COUNT": "N", "RESULTS": "N", "SCOPED": "N",
        }
        assert runs["ARGUMENTS"][0] == runs["RESULTS"][0] == "JSON"
        assert runs["SCOPED"][0] == "BOOLEAN"
        links = columns_of(cur, "CCCTX_MEMORY_RUN_REPOS")
        assert {c: v[1] for c, v in links.items()} == {"RUN_ID": "N", "REPO_ID": "N", "CONSOLIDATED": "N"}
        cur.execute("select column_name from user_ind_columns where table_name = 'CCCTX_MEMORY_RUN_REPOS'"
                    " and column_position = 1")
        assert "REPO_ID" in {row[0] for row in cur}
        cur.execute("select table_name from user_tables where table_name like 'CCCTX_MEM\\_%' escape '\\'")
        assert "CCCTX_MEM_MEMORY" in {row[0] for row in cur}  # the package's tables come from this migration


def test_memory_run_defaults_and_status_check(conn, repo_id):
    with conn.cursor() as cur:
        run_id = add_run(cur)
        cur.execute("insert into ccctx_memory_run_repos (run_id, repo_id) values (:r, :p)", r=run_id, p=repo_id)
        called, scoped = cur.execute("select called_at, scoped from ccctx_memory_runs where id = :i",
                                     i=run_id).fetchone()
        assert called is not None and scoped is False
        assert cur.execute("select consolidated from ccctx_memory_run_repos where run_id = :i",
                           i=run_id).fetchone() == (False,)
        with pytest.raises(oracledb.DatabaseError, match="CCCTX_MEMORY_RUNS_STATUS_CK"):
            add_run(cur, status="done")
        with pytest.raises(oracledb.IntegrityError):
            cur.execute("insert into ccctx_memory_run_repos (run_id, repo_id) values (:r, :p)", r=run_id, p=repo_id)
    conn.rollback()


def test_memory_run_and_repo_delete_cascade_links(conn, repo_id):
    with conn.cursor() as cur:
        kept, gone = add_run(cur), add_run(cur)
        for run_id in (kept, gone):
            cur.execute("insert into ccctx_memory_run_repos (run_id, repo_id) values (:r, :p)", r=run_id, p=repo_id)
        cur.execute("delete from ccctx_memory_runs where id = :i", i=gone)
        assert cur.execute("select count(*) from ccctx_memory_run_repos where run_id = :i", i=gone).fetchone()[0] == 0
        cur.execute("delete from ccctx_repos where id = :i", i=repo_id)
        assert cur.execute("select count(*) from ccctx_memory_run_repos where run_id = :i", i=kept).fetchone()[0] == 0
        assert cur.execute("select count(*) from ccctx_memory_runs where id = :i", i=kept).fetchone()[0] == 1
    conn.rollback()


def test_usage_feedback_table(conn):
    with conn.cursor() as cur:
        cur.execute("select name from ccctx_migrations where version = 9")
        assert cur.fetchone() == ("usage feedback",)
        uses = columns_of(cur, "CCCTX_FEEDBACK")
        assert {c: v[1] for c, v in uses.items()} == {
            "ID": "N", "REPO_ID": "N", "PATH": "N", "NAME": "N", "KIND": "N", "HOW": "N", "CLIENT": "Y",
            "SESSION_ID": "N", "RUN_ID": "Y", "USED_AT": "N",
        }
        assert uses["USED_AT"][0].startswith("TIMESTAMP")
        cur.execute("select column_name from user_ind_columns where index_name = 'CCCTX_FEEDBACK_RESULT_IX'"
                    " order by column_position")
        assert [row[0] for row in cur] == ["REPO_ID", "NAME"]


def test_use_how_check_and_default_time(conn, repo_id):
    with conn.cursor() as cur:
        use = add_use(cur, repo_id, "opened")
        assert cur.execute("select used_at from ccctx_feedback where id = :i", i=use).fetchone()[0] is not None
        with pytest.raises(oracledb.DatabaseError, match="CCCTX_FEEDBACK_HOW_CK"):
            add_use(cur, repo_id, "liked")
    conn.rollback()


def test_uses_go_with_their_repository_and_outlive_their_run(conn, repo_id):
    with conn.cursor() as cur:
        run_id = add_run(cur)
        use = add_use(cur, repo_id, run_id=run_id)
        cur.execute("delete from ccctx_memory_runs where id = :i", i=run_id)
        assert cur.execute("select run_id from ccctx_feedback where id = :i", i=use).fetchone() == (None,)
        cur.execute("delete from ccctx_repos where id = :i", i=repo_id)
        assert cur.execute("select count(*) from ccctx_feedback where id = :i", i=use).fetchone()[0] == 0
    conn.rollback()
