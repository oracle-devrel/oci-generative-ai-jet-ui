"""vector_memory_size management. Mirrors notebook §3.2.1.

vector_memory_size is a static *instance-wide* parameter — setting it requires
SPFILE scope + a database bounce. We always set it at CDB-root (CONTAINER=ALL)
because PDB scope doesn't actually allocate the SGA pool.

CRITICAL: `ALTER SYSTEM ... CONTAINER=ALL` is only legal from CDB$ROOT — running
it from a PDB session raises ORA-02065. `connect_sys()` lands in FREEPDB1, so
we must `ALTER SESSION SET CONTAINER = CDB$ROOT` before any ALTER SYSTEM that
uses CONTAINER=ALL. We switch back to FREEPDB1 after.
"""

import oracledb


def _switch_to_root(cur):
    try:
        cur.execute("ALTER SESSION SET CONTAINER = CDB$ROOT")
    except oracledb.DatabaseError:
        # Already in root, or a non-CDB build. Either way, continue.
        pass


def _switch_to_pdb(cur, pdb_name: str = "FREEPDB1"):
    try:
        cur.execute(f"ALTER SESSION SET CONTAINER = {pdb_name}")
    except oracledb.DatabaseError:
        pass


def get_running_mb(sys_conn) -> int:
    """Return the live vector_memory_size in MB (0 if pool isn't allocated).

    Queries `v$parameter` from CDB$ROOT — the pool is instance-wide so we want
    the CDB view, not whatever the PDB-level override happens to be.
    """
    with sys_conn.cursor() as cur:
        _switch_to_root(cur)
        cur.execute(
            "SELECT NVL(value, '0') FROM v$parameter WHERE name = 'vector_memory_size'"
        )
        row = cur.fetchone()
        _switch_to_pdb(cur)
    return int(row[0] or 0) // (1024 * 1024) if row else 0


def get_spfile_mb(sys_conn) -> int:
    """Return the SPFILE-stored vector_memory_size in MB (CDB-root scope)."""
    with sys_conn.cursor() as cur:
        _switch_to_root(cur)
        cur.execute(
            "SELECT NVL(value, '0') FROM v$spparameter WHERE name = 'vector_memory_size'"
        )
        row = cur.fetchone()
        _switch_to_pdb(cur)
    return int(row[0] or 0) // (1024 * 1024) if row else 0


def set_spfile(sys_conn, size_mb: int = 512):
    """Set vector_memory_size in the SPFILE at CDB-root scope.

    Takes effect on the next instance bounce. Falls back to PDB-scope without
    CONTAINER=ALL on non-multitenant builds.
    """
    with sys_conn.cursor() as cur:
        _switch_to_root(cur)

        # Defensive RESET in case a previous (incorrectly scoped) value is lingering.
        try:
            cur.execute("ALTER SYSTEM RESET vector_memory_size SCOPE=SPFILE")
        except oracledb.DatabaseError:
            pass

        try:
            cur.execute(
                f"ALTER SYSTEM SET vector_memory_size = {size_mb}M "
                "SCOPE=SPFILE CONTAINER=ALL"
            )
        except oracledb.DatabaseError as e:
            # ORA-02065 (illegal option) — e.g. on a non-CDB or older build that
            # doesn't accept CONTAINER=ALL. Retry without it.
            if e.args[0].code in (2065, 65040):
                cur.execute(
                    f"ALTER SYSTEM SET vector_memory_size = {size_mb}M SCOPE=SPFILE"
                )
            else:
                _switch_to_pdb(cur)
                raise

        _switch_to_pdb(cur)
    sys_conn.commit()


def needs_bounce(sys_conn, target_mb: int = 512) -> bool:
    """True if SPFILE has the target value but the running instance hasn't picked it up."""
    return get_running_mb(sys_conn) < target_mb <= get_spfile_mb(sys_conn)
