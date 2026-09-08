"""Oracle connection helpers shared by the backend.

We open exactly three connections for the whole process lifetime:

- One **sync** `oracledb.Connection` for `OracleVS` + `OracleEmbeddings`.
- One **async** connection for `AsyncOracleSaver` (per-thread checkpoints).
- One **async** connection for `AsyncOracleStore` (long-term memory).

The agent module reaches in here for the three handles via the helpers
below.
"""

from __future__ import annotations

import oracledb
from app.backend.config import (
    ORACLE_AUTH_SYSDBA,
    ORACLE_DSN,
    ORACLE_PASSWORD,
    ORACLE_USER,
)


def _kwargs() -> dict:
    kw = {"user": ORACLE_USER, "password": ORACLE_PASSWORD, "dsn": ORACLE_DSN}
    if ORACLE_AUTH_SYSDBA:
        kw["mode"] = oracledb.AUTH_MODE_SYSDBA
    return kw


_sync_client: oracledb.Connection | None = None
_saver_conn = None
_store_conn = None


def sync_client() -> oracledb.Connection:
    """Module-level singleton sync connection."""
    global _sync_client
    if _sync_client is None:
        _sync_client = oracledb.connect(**_kwargs())
    return _sync_client


async def saver_connection():
    global _saver_conn
    if _saver_conn is None:
        _saver_conn = await oracledb.connect_async(**_kwargs())
    return _saver_conn


async def store_connection():
    global _store_conn
    if _store_conn is None:
        _store_conn = await oracledb.connect_async(**_kwargs())
    return _store_conn


async def close_all() -> None:
    global _sync_client, _saver_conn, _store_conn
    if _sync_client is not None:
        try:
            _sync_client.close()
        except Exception:
            pass
        _sync_client = None
    if _saver_conn is not None:
        try:
            await _saver_conn.close()
        except Exception:
            pass
        _saver_conn = None
    if _store_conn is not None:
        try:
            await _store_conn.close()
        except Exception:
            pass
        _store_conn = None
