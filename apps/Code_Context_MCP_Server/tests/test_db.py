"""The database check: connecting, the version and vector check, and exit codes."""

import time

import oracledb
import pytest

from golestan_code_mcp import db
from golestan_code_mcp.config import load


@pytest.fixture(scope="module")
def cfg():
    try:
        cfg = load()
        db.connect(cfg).close()
    except Exception as e:  # config missing or database down: skip, never fail
        pytest.skip(f"database unreachable: {type(e).__name__}")
    return cfg


def test_unreachable_reports_reason_without_secret():
    cfg = load({"DB_USER": "nobody", "DB_PASSWORD": "Not-A-Real-Pw-42", "DB_PORT": "1"}, dotenv_path=None)
    started = time.monotonic()
    result = db.check(cfg, wait=0)
    assert not result.ok and result.reason
    assert "Not-A-Real-Pw-42" not in result.reason
    assert time.monotonic() - started < 5


def test_check_ok(cfg):
    result = db.check(cfg, wait=0)
    assert result.ok, result.reason
    assert result.version and result.vector_ok


def test_smoke_rows_grow(cfg):
    with db.connect(cfg) as conn, conn.cursor() as cur:
        try:
            cur.execute(
                "create table ccctx_smoke (id number generated always as identity primary key,"
                " created_at timestamp default systimestamp not null)"
            )
        except oracledb.DatabaseError as e:
            if e.args[0].full_code != "ORA-00955":  # already exists
                raise
        before = db.check(cfg, wait=0).smoke_rows or 0
        cur.execute("insert into ccctx_smoke (created_at) values (default)")
        conn.commit()
    assert db.check(cfg, wait=0).smoke_rows == before + 1


def test_main_output_has_no_secret(cfg, capsys):
    assert db.main(["--wait", "0"]) == 0
    out = capsys.readouterr()
    assert "vector: ok (VECTOR)" in out.out
    assert cfg.db_password not in out.out + out.err
