"""Unit tests for the flag-gated checkpointer resolver.

These cover the failure / lifecycle paths that do NOT need a live Oracle DB
(they mock the pool + saver), so they run in CI on the default flag. The live
durability round-trip lives in test_oracle_checkpointer.py.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from langgraph.checkpoint.memory import MemorySaver

import concierge.checkpointer as cp


@pytest.fixture(autouse=True)
def _reset_globals():
    """Each test starts and ends with clean module globals."""
    cp._pool = None
    cp._saver = None
    yield
    cp._pool = None
    cp._saver = None


def _set_oracle_env(monkeypatch):
    monkeypatch.setenv("LANGGRAPH_CHECKPOINTER", "oracle")
    monkeypatch.setenv("ORACLE_DB_USER", "u")
    monkeypatch.setenv("ORACLE_DB_PASSWORD", "p")
    monkeypatch.setenv("ORACLE_DB_DSN", "localhost:1521/X")


async def test_init_closes_pool_when_setup_fails(monkeypatch):
    """If setup() raises, init must close the already-opened pool (no leak) and
    degrade to MemorySaver."""
    _set_oracle_env(monkeypatch)

    fake_pool = MagicMock()
    fake_pool.close = AsyncMock()
    monkeypatch.setattr(
        cp.oracledb, "create_pool_async", MagicMock(return_value=fake_pool)
    )

    fake_saver = MagicMock()
    fake_saver.setup = AsyncMock(side_effect=RuntimeError("DDL boom"))
    monkeypatch.setattr(cp, "AsyncOracleSaver", MagicMock(return_value=fake_saver))

    await cp.init_checkpointer()

    fake_pool.close.assert_awaited_once()  # the leak fix: pool closed, not orphaned
    assert cp._pool is None and cp._saver is None
    assert isinstance(cp.resolve_checkpointer(), MemorySaver)  # degraded silently


async def test_init_is_idempotent(monkeypatch):
    """A second init while a saver is already set must not build another pool."""
    _set_oracle_env(monkeypatch)
    cp._saver = object()  # pretend a prior init already succeeded

    create = MagicMock()
    monkeypatch.setattr(cp.oracledb, "create_pool_async", create)

    await cp.init_checkpointer()

    create.assert_not_called()


async def test_resolve_defaults_to_memory_when_flag_unset(monkeypatch):
    monkeypatch.delenv("LANGGRAPH_CHECKPOINTER", raising=False)
    assert isinstance(cp.resolve_checkpointer(), MemorySaver)


async def test_init_is_noop_when_flag_not_oracle(monkeypatch):
    monkeypatch.setenv("LANGGRAPH_CHECKPOINTER", "memory")
    create = MagicMock()
    monkeypatch.setattr(cp.oracledb, "create_pool_async", create)

    await cp.init_checkpointer()

    create.assert_not_called()
    assert cp._saver is None
