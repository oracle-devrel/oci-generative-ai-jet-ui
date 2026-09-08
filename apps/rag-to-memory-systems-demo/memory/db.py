"""Database connection helpers."""
from __future__ import annotations
import os
import oracledb
from dotenv import load_dotenv

load_dotenv()


def env_dsn() -> tuple[str, str, str]:
    """Read Oracle connection settings from environment.

    Returns: (username, password, dsn)
    """
    return (
        os.getenv("ORACLE_DB_USERNAME", "memory_demo"),
        os.getenv("ORACLE_DB_PASSWORD", "memory_demo"),
        os.getenv("ORACLE_DB_DSN", "localhost:1521/FREEPDB1"),
    )


async def connect() -> oracledb.AsyncConnection:
    """Open an async connection to Oracle AI Database using env settings."""
    user, password, dsn = env_dsn()
    return await oracledb.connect_async(user=user, password=password, dsn=dsn)


def connect_sync() -> oracledb.Connection:
    """Synchronous variant for DDL setup scripts and seed data."""
    user, password, dsn = env_dsn()
    return oracledb.connect(user=user, password=password, dsn=dsn)
