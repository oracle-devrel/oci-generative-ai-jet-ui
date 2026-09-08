"""Idempotent DBFS setup — tablespace, store, and mount.

Mirrors notebook §7.1 + §7.2's create-and-mount cells, condensed into one
re-runnable function. Re-running on an already-set-up DB is a no-op.
"""

import os.path

import oracledb

from db.dbfs import DBFS_MOUNT, DBFS_STORE, DBFS_TABLESPACE


_DBFS_EXISTS_CODES = (955, 64007, 64008, 1)  # 1 = unique constraint on DBFS$_STORES/DBFS$_MOUNTS


def ensure_tablespace(sys_conn, agent_user: str):
    with sys_conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) FROM dba_tablespaces WHERE tablespace_name = :n",
            n=DBFS_TABLESPACE,
        )
        if cur.fetchone()[0] == 0:
            cur.execute("SELECT name FROM v$datafile WHERE rownum = 1")
            sample_path = cur.fetchone()[0]
            dbfs_dir = os.path.dirname(sample_path)
            dbfs_path = f"{dbfs_dir}/agent_dbfs01.dbf"
            cur.execute(
                f"CREATE TABLESPACE {DBFS_TABLESPACE} "
                f"DATAFILE '{dbfs_path}' SIZE 100M AUTOEXTEND ON NEXT 50M MAXSIZE 2G"
            )
            print(f"  created tablespace {DBFS_TABLESPACE} at {dbfs_path}")
        else:
            print(f"  tablespace {DBFS_TABLESPACE} already exists")
        cur.execute(f"ALTER USER {agent_user} QUOTA UNLIMITED ON {DBFS_TABLESPACE}")
    sys_conn.commit()


def ensure_store_and_mount(agent_conn):
    create_fs = (
        "BEGIN "
        "  DBMS_DBFS_SFS.CREATEFILESYSTEM("
        f"    store_name => '{DBFS_STORE}',"
        f"    tbl_name   => '{DBFS_STORE}_T',"
        f"    tbl_tbs    => '{DBFS_TABLESPACE}',"
        "    use_bf     => FALSE); "
        "END;"
    )
    register = (
        "BEGIN "
        "  DBMS_DBFS_CONTENT.REGISTERSTORE("
        f"    store_name => '{DBFS_STORE}',"
        "    provider_name => 'sample1',"
        "    provider_package => 'DBMS_DBFS_SFS'); "
        "END;"
    )
    mount = (
        "BEGIN "
        "  DBMS_DBFS_CONTENT.MOUNTSTORE("
        f"    store_name => '{DBFS_STORE}',"
        f"    store_mount => '{DBFS_MOUNT.lstrip('/')}'); "
        "END;"
    )
    with agent_conn.cursor() as cur:
        for label, stmt in [("createfilesystem", create_fs),
                            ("registerstore", register),
                            ("mountstore", mount)]:
            try:
                cur.execute(stmt)
                print(f"  {label}: ok")
            except oracledb.DatabaseError as e:
                err_code = e.args[0].code if e.args else None
                err_text = str(e)
                if err_code in _DBFS_EXISTS_CODES or "already exists" in err_text.lower():
                    print(f"  {label}: (already exists)")
                else:
                    print(f"  {label}: {e}")
    agent_conn.commit()


def ensure(sys_conn, agent_conn, agent_user: str):
    """Top-level: ensure the tablespace + store + mount exist."""
    print("Ensuring DBFS tablespace...")
    ensure_tablespace(sys_conn, agent_user)
    print("Ensuring DBFS store + mount...")
    ensure_store_and_mount(agent_conn)
