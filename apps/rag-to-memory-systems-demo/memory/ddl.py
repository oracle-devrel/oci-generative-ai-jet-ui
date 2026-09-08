"""Idempotent DDL runner.

CLI: python -m memory.ddl setup | teardown | reset
"""
from __future__ import annotations
import sys
from pathlib import Path
import oracledb
from memory.db import connect_sync

SCHEMAS_FILE = Path(__file__).parent / "schemas.sql"

TABLES = [
    "policy_memory", "preference_memory", "fact_memory",
    "episodic_memory", "trace_memory", "deletion_events",
]


def drop_all(conn: oracledb.Connection) -> None:
    cur = conn.cursor()
    for tbl in TABLES:
        try:
            cur.execute(f"DROP TABLE {tbl} PURGE")
        except oracledb.DatabaseError as e:
            (err,) = e.args
            if err.code != 942:  # ORA-00942: table does not exist
                raise
    conn.commit()


def _strip_comments(segment: str) -> str:
    """Remove leading SQL comment lines from a segment, return remaining text."""
    lines = segment.splitlines()
    non_comment = []
    for line in lines:
        if line.strip().startswith("--"):
            # Skip leading comment lines, but once we have real SQL keep everything
            if non_comment:
                non_comment.append(line)
        else:
            non_comment.append(line)
    return "\n".join(non_comment).strip()


def create_all(conn: oracledb.Connection) -> None:
    sql = SCHEMAS_FILE.read_text()
    cur = conn.cursor()
    raw_segments = [s.strip() for s in sql.split(";") if s.strip()]
    statements = [_strip_comments(s) for s in raw_segments]
    statements = [s for s in statements if s and not s.startswith("--")]
    for stmt in statements:
        try:
            cur.execute(stmt)
        except oracledb.DatabaseError as e:
            (err,) = e.args
            # ORA-29855: error occurred in the execution of ODCIINDEXCREATE routine
            # This fires when CTXSYS.CONTEXT index can't be created without CTXAPP grant.
            # We log and continue — the cascade fallback in retrieval.py handles this.
            if err.code == 29855 and "CTXSYS.CONTEXT" in stmt.upper():
                print(f"  (skipped Oracle Text index: CTXAPP role not granted to current user)")
                continue
            raise
    conn.commit()


def main() -> None:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "setup"
    conn = connect_sync()
    try:
        if cmd == "setup":
            create_all(conn)
            print(f"Created {len(TABLES)} tables.")
        elif cmd == "teardown":
            drop_all(conn)
            print("Dropped all tables.")
        elif cmd == "reset":
            drop_all(conn)
            create_all(conn)
            print(f"Reset {len(TABLES)} tables.")
        else:
            print(f"Unknown command: {cmd}. Use setup | teardown | reset.")
            sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
