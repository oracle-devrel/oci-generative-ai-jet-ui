#!/usr/bin/env python3
"""Bootstrap Oracle for the supply-chain demand-planning workshop.

Runs once during Codespace post-create. Idempotent — safe to re-run.

Steps:
1. Connect as SYSTEM (or SYS-as-SYSDBA), create AGENT user if missing.
2. Grant the privileges AGENT needs: CONNECT, RESOURCE, plus the trio
   required to load an ONNX model and run vector search
   (CREATE MINING MODEL, CREATE PROCEDURE, CREATE ANY DIRECTORY).
3. Allocate the vector memory pool (`vector_memory_size`) if it isn't
   already large enough — required for HNSW indexes on a fresh container.

The ONNX model load itself is a separate step (`onnx_setup.py`) so it can
be re-run independently when the model changes.
"""

from __future__ import annotations

import os

import oracledb

SYSTEM_USER = os.environ.get("ORACLE_SYSTEM_USER", "system")
SYSTEM_PASSWORD = os.environ.get("ORACLE_SYSTEM_PASSWORD") or os.environ.get("ORACLE_PWD", "mypw")
DSN = os.environ.get("ORACLE_DSN", "localhost:1521/FREEPDB1")

AGENT_USER = os.environ.get("AGENT_USER", "AGENT")
AGENT_PASSWORD = os.environ.get("AGENT_PASSWORD", "AgentPwd_2025")

VECTOR_POOL_MB = int(os.environ.get("VECTOR_MEMORY_MB", "512"))


def _user_exists(cur, user: str) -> bool:
    cur.execute("SELECT COUNT(*) FROM all_users WHERE username = :u", u=user.upper())
    (n,) = cur.fetchone()
    return n > 0


def _create_agent_user(conn) -> None:
    cur = conn.cursor()
    if _user_exists(cur, AGENT_USER):
        print(f"[bootstrap] user {AGENT_USER} already exists — skipping create.")
    else:
        print(f"[bootstrap] creating user {AGENT_USER} …")
        cur.execute(
            f'CREATE USER "{AGENT_USER}" IDENTIFIED BY "{AGENT_PASSWORD}" '
            f"DEFAULT TABLESPACE USERS QUOTA UNLIMITED ON USERS"
        )
    # Privileges (idempotent)
    grants = [
        "CONNECT",
        "RESOURCE",
        "CREATE SESSION",
        "CREATE TABLE",
        "CREATE VIEW",
        "CREATE PROCEDURE",
        "CREATE MINING MODEL",
        "CREATE ANY DIRECTORY",
        "DB_DEVELOPER_ROLE",
    ]
    for g in grants:
        try:
            cur.execute(f'GRANT {g} TO "{AGENT_USER}"')
        except oracledb.DatabaseError as e:
            err = str(e)
            # ORA-01919: role does not exist — skip granting that role on this image
            if "ORA-01919" in err or "ORA-01031" in err:
                print(f"[bootstrap] skip GRANT {g}: {err.splitlines()[0]}")
            else:
                raise
    conn.commit()


def _ensure_vector_pool(conn) -> None:
    cur = conn.cursor()
    try:
        cur.execute("SELECT value FROM v$parameter WHERE name = 'vector_memory_size'")
        (current,) = cur.fetchone()
    except oracledb.DatabaseError as e:
        print(f"[bootstrap] could not read vector_memory_size: {e}")
        return

    current_mb = int(current or 0) // (1024 * 1024)
    if current_mb >= VECTOR_POOL_MB:
        print(f"[bootstrap] vector_memory_size already {current_mb}M (>= {VECTOR_POOL_MB}M).")
        return

    print(
        f"[bootstrap] setting vector_memory_size = {VECTOR_POOL_MB}M (scope=spfile) — restart required for it to take effect."
    )
    cur.execute(f"ALTER SYSTEM SET vector_memory_size = {VECTOR_POOL_MB}M SCOPE=spfile")


def main() -> int:
    print("=" * 60)
    print("Supply-chain demand-planning workshop — bootstrap step")
    print("=" * 60)

    # Connect as a privileged user. Try regular SYSTEM first; if that's not
    # the right one, fall back to SYS-as-SYSDBA.
    try:
        conn = oracledb.connect(user=SYSTEM_USER, password=SYSTEM_PASSWORD, dsn=DSN)
    except oracledb.DatabaseError as e:
        if "ORA-28009" in str(e):
            print("[bootstrap] SYSTEM rejected with ORA-28009; retrying as SYS-as-SYSDBA …")
            conn = oracledb.connect(
                user="sys",
                password=SYSTEM_PASSWORD,
                dsn=DSN,
                mode=oracledb.AUTH_MODE_SYSDBA,
            )
        else:
            raise

    _create_agent_user(conn)
    _ensure_vector_pool(conn)

    print()
    print(f"✅ Bootstrap complete. AGENT user is {AGENT_USER}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
