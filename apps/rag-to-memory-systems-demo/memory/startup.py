"""Startup probes:
  * lexical_available — Oracle Text CONTEXT index on fact_memory present?
  * schema_ready      — all six demo tables present in this schema?
"""
from __future__ import annotations
import oracledb

_REQUIRED_TABLES = (
    "POLICY_MEMORY", "PREFERENCE_MEMORY", "FACT_MEMORY",
    "EPISODIC_MEMORY", "TRACE_MEMORY", "DELETION_EVENTS",
)


async def lexical_available(conn: oracledb.AsyncConnection) -> bool:
    cur = conn.cursor()
    try:
        await cur.execute(
            """
            SELECT COUNT(*) FROM user_indexes
             WHERE table_name = 'FACT_MEMORY' AND ityp_owner = 'CTXSYS'
            """
        )
        (n,) = await cur.fetchone()
        return n > 0
    except oracledb.DatabaseError:
        return False


async def schema_ready(conn: oracledb.AsyncConnection) -> tuple[bool, list[str]]:
    """Return (all_present, missing_table_names) for the demo schema."""
    cur = conn.cursor()
    placeholders = ", ".join(f":t{i}" for i in range(len(_REQUIRED_TABLES)))
    binds = {f"t{i}": name for i, name in enumerate(_REQUIRED_TABLES)}
    try:
        await cur.execute(
            f"SELECT table_name FROM user_tables WHERE table_name IN ({placeholders})",
            **binds,
        )
        present = {row[0] async for row in cur}
    except oracledb.DatabaseError:
        return False, list(_REQUIRED_TABLES)
    missing = [t for t in _REQUIRED_TABLES if t not in present]
    return not missing, missing
