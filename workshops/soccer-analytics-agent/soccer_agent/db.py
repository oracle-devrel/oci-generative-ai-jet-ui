"""Oracle connection helpers for the soccer analytics agent."""

from __future__ import annotations

import logging
import os
import threading
from contextlib import contextmanager

import oracledb
from dotenv import load_dotenv

load_dotenv()

LOGGER = logging.getLogger(__name__)

# Process-lifetime connection pool for the soccer user.  Created lazily on
# first use so unit tests that monkeypatch env vars before importing this
# module still pick up the correct credentials.  A small pool (min=1, max=4)
# eliminates the per-request TCP handshake cost while keeping the footprint
# small for the workshop container.
_pool: oracledb.ConnectionPool | None = None
_pool_lock = threading.Lock()
# Snapshot of the credentials used when the pool was created.  If the env
# vars change (e.g. conftest redirects to a test schema) the pool is
# transparently recreated.
_pool_key: tuple[str, str, str] = ("", "", "")


def _dsn() -> str:
    return os.environ["ORACLE_DSN"]


def _get_pool() -> oracledb.ConnectionPool:
    """Return the process-lifetime pool, creating or recreating it as needed."""
    global _pool, _pool_key
    user = os.environ["ORACLE_USER"]
    password = os.environ["ORACLE_PASSWORD"]
    dsn = _dsn()
    current_key = (user, password, dsn)
    with _pool_lock:
        if _pool is None or _pool_key != current_key:
            if _pool is not None:
                try:
                    _pool.close(force=True)
                except Exception:
                    pass
            _pool = oracledb.create_pool(
                user=user,
                password=password,
                dsn=dsn,
                min=1,
                max=4,
                increment=1,
            )
            _pool_key = current_key
            LOGGER.debug("Oracle connection pool created (user=%s dsn=%s)", user, dsn)
    return _pool


@contextmanager
def get_connection():
    """Acquire a connection from the pool (or fall back to a direct connect)."""
    try:
        pool = _get_pool()
        conn = pool.acquire()
    except Exception:
        # Direct connect fallback keeps unit tests and unusual environments
        # working even when the pool cannot be initialised.
        conn = oracledb.connect(
            user=os.environ["ORACLE_USER"],
            password=os.environ["ORACLE_PASSWORD"],
            dsn=_dsn(),
        )
        try:
            yield conn
        finally:
            conn.close()
        return
    try:
        yield conn
    finally:
        pool.release(conn)


@contextmanager
def get_admin_connection():
    """Connect as SYSTEM for schema bootstrap (always a direct connection)."""
    conn = oracledb.connect(
        user="system",
        password=os.environ["ORACLE_ADMIN_PASSWORD"],
        dsn=_dsn(),
    )
    try:
        yield conn
    finally:
        conn.close()
