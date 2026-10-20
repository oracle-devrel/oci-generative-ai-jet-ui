"""Database connection and the golestan-check-db connectivity check."""

import argparse
import sys
import time
from dataclasses import dataclass

import oracledb

from golestan_code_mcp.config import Config, ConfigError, load

# Listener answers but the pluggable database is not open yet.
STARTING_CODES = {"ORA-01033", "ORA-01109", "ORA-12514", "ORA-12528", "DPY-6001"}
VECTOR_SQL = "select vector_dimension_count(to_vector('[1,2,3]')) from dual"


@dataclass
class CheckResult:
    ok: bool
    version: str | None = None
    vector_ok: bool = False
    smoke_rows: int | None = None
    reason: str | None = None


def connect(cfg: Config, timeout: float = 3) -> oracledb.Connection:
    return oracledb.connect(
        user=cfg.db_user, password=cfg.db_password, dsn=cfg.dsn, tcp_connect_timeout=timeout, retry_count=0
    )


def describe(error: oracledb.Error) -> str:
    """One-line cause from a driver error. Driver messages never include the password."""
    err = error.args[0]
    return str(getattr(err, "message", err)).splitlines()[0]


def check(cfg: Config, wait: float = 0) -> CheckResult:
    """Log in, read the version, prove VECTOR works. Retry until `wait` seconds pass, except on bad login."""
    deadline = time.monotonic() + wait
    while True:
        try:
            with connect(cfg) as conn, conn.cursor() as cur:
                result = CheckResult(ok=False, version=conn.version)
                try:
                    cur.execute(VECTOR_SQL)
                    result.vector_ok = cur.fetchone()[0] == 3
                except oracledb.DatabaseError as e:
                    result.reason = f"VECTOR check failed: {describe(e)}"
                    return result
                cur.execute("select count(*) from user_tables where table_name = 'CCCTX_SMOKE'")
                if cur.fetchone()[0]:
                    cur.execute("select count(*) from ccctx_smoke")
                    result.smoke_rows = cur.fetchone()[0]
                result.ok = result.vector_ok
                if not result.ok:
                    result.reason = "VECTOR check failed: unexpected dimension count"
                return result
        except oracledb.Error as e:
            code = getattr(e.args[0], "full_code", "")
            if code == "ORA-01017":
                return CheckResult(ok=False, reason=f"login failed for {cfg.db_user}")
            reason = "still starting" if code in STARTING_CODES else f"unreachable: {describe(e)}"
            if time.monotonic() >= deadline:
                return CheckResult(ok=False, reason=reason)
            time.sleep(5)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="golestan-check-db", description="Check the database connection.")
    parser.add_argument("--wait", type=float, default=300, help="seconds to wait for a starting database")
    args = parser.parse_args(argv)
    try:
        cfg = load()
    except ConfigError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    result = check(cfg, wait=args.wait)
    if not result.ok:
        print(f"error: {result.reason}", file=sys.stderr)
        return 3 if result.version else 2
    print(f"connected: {cfg.db_user}@{cfg.dsn}")
    print(f"version: {result.version}")
    print("vector: ok (VECTOR)")
    print(f"ccctx_smoke rows: {result.smoke_rows if result.smoke_rows is not None else 'table not created yet'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
