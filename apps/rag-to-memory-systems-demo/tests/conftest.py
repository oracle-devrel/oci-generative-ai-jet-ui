"""Pytest fixtures shared across tests.

Provides a session-scoped async Oracle connection via the `db` fixture.
"""
import pytest
from dotenv import load_dotenv
import oracledb
from memory.db import env_dsn

load_dotenv()


@pytest.fixture(scope="session")
async def db():
    """Async Oracle connection, opened once per pytest session."""
    user, password, dsn = env_dsn()
    conn = await oracledb.connect_async(user=user, password=password, dsn=dsn)
    yield conn
    await conn.close()
