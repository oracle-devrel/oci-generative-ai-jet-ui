"""Idempotently create the AGENT user with all grants the harness needs.

Mirrors the notebook's §3.2 cell. SYSDBA-only.
"""

import oracledb


AGENT_GRANTS = [
    "CONNECT, RESOURCE, CREATE SESSION",
    "CREATE TABLE, CREATE SEQUENCE, CREATE VIEW, CREATE PROCEDURE",
    "UNLIMITED TABLESPACE",
    # Scanner needs catalog views
    "SELECT_CATALOG_ROLE",
    # MLE
    "EXECUTE ON DBMS_MLE",
    "DB_DEVELOPER_ROLE",
    "EXECUTE DYNAMIC MLE",
    # DBFS scratchpad
    "EXECUTE ON DBMS_DBFS_CONTENT",
    "EXECUTE ON DBMS_DBFS_SFS",
    "DBFS_ROLE",
    # ONNX model loading (notebook §3.4.2)
    "CREATE MINING MODEL",
]

# Per-object grants that need separate statements (V$ views).
SYS_OBJECT_GRANTS = [
    "SELECT ON SYS.V_$SQL",
    "SELECT ON SYS.V_$SQLSTATS",
]


def ensure_agent_user(sys_conn, agent_user: str, agent_pass: str):
    """Create the AGENT user if missing, then apply all grants idempotently."""
    with sys_conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) FROM all_users WHERE username = :u",
            u=agent_user.upper(),
        )
        exists = cur.fetchone()[0] > 0
        if not exists:
            cur.execute(f"CREATE USER {agent_user} IDENTIFIED BY {agent_pass}")
            print(f"  created user {agent_user}")
        else:
            print(f"  user {agent_user} already exists")

        for grant in AGENT_GRANTS:
            try:
                cur.execute(f"GRANT {grant} TO {agent_user}")
            except oracledb.DatabaseError as e:
                code_ = e.args[0].code
                # Some roles aren't grantable on all images; tolerate.
                if code_ in (1031, 1924, 1919):
                    print(f"  skip GRANT {grant!r}: {e}")
                else:
                    raise

        for grant in SYS_OBJECT_GRANTS:
            try:
                cur.execute(f"GRANT {grant} TO {agent_user}")
            except oracledb.DatabaseError as e:
                if e.args[0].code == 1031:
                    print(f"  skip GRANT {grant!r}: insufficient privilege")
                else:
                    raise

    sys_conn.commit()
    print(f"  grants applied to {agent_user}")
