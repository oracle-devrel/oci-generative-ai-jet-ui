"""Database connection helpers."""
from __future__ import annotations
import os
from pathlib import Path
import oracledb
from dotenv import load_dotenv
oracledb.defaults.program = "devrel-developerhub-rag-to-memory-systems-demo"

# Demo settings (tenant, user, OpenAI) live in this app's .env. Database credentials come
# from the repository-root .env that the Developer Hub notebooks share. load_dotenv never
# overrides a variable that is already set, so the app's .env wins where both define one.
_APP_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_APP_ROOT / ".env")
for _parent in _APP_ROOT.parents:
    if (_parent / ".env").is_file():
        load_dotenv(_parent / ".env")
        break


def env_dsn() -> tuple[str, str, str]:
    """Read Oracle connection settings from environment.

    Returns: (username, password, dsn)
    """
    return (
        os.getenv("DB_USER", "memory_demo"),
        os.getenv("DB_PASSWORD", "memory_demo"),
        os.getenv("DB_DSN", "localhost:1521/FREEPDB1"),
    )


async def connect() -> oracledb.AsyncConnection:
    """Open an async connection to Oracle AI Database using env settings."""
    user, password, dsn = env_dsn()
    return await oracledb.connect_async(user=user, password=password, dsn=dsn)


def connect_sync() -> oracledb.Connection:
    """Synchronous variant for DDL setup scripts and seed data."""
    user, password, dsn = env_dsn()
    return oracledb.connect(user=user, password=password, dsn=dsn)
