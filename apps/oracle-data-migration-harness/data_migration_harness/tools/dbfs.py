"""Layer 4 helper: Oracle Database File System scratchpad for stage artefacts."""

import json

from data_migration_harness.environment import oracle_pool


def init_dbfs_table():
    pool = oracle_pool()
    with pool.acquire() as conn:
        cur = conn.cursor()
        try:
            cur.execute(
                """
                CREATE TABLE dbfs_scratch (
                    path VARCHAR2(256) PRIMARY KEY,
                    content CLOB NOT NULL,
                    written_at TIMESTAMP DEFAULT SYSTIMESTAMP
                )
            """
            )
        except Exception:
            pass
        conn.commit()


def write(path: str, content):
    if isinstance(content, dict):
        content = json.dumps(content, default=str, indent=2)
    pool = oracle_pool()
    with pool.acquire() as conn:
        cur = conn.cursor()
        cur.execute(
            "MERGE INTO dbfs_scratch d USING dual ON (d.path = :p) "
            "WHEN MATCHED THEN UPDATE SET content = :c, written_at = SYSTIMESTAMP "
            "WHEN NOT MATCHED THEN INSERT (path, content) VALUES (:p, :c)",
            {"p": path, "c": content},
        )
        conn.commit()


def read(path: str) -> str | None:
    pool = oracle_pool()
    with pool.acquire() as conn:
        cur = conn.cursor()
        cur.execute("SELECT content FROM dbfs_scratch WHERE path = :p", {"p": path})
        row = cur.fetchone()
        if row is None:
            return None
        clob = row[0]
        return clob.read() if hasattr(clob, "read") else str(clob)
