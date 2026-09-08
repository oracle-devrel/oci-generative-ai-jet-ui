"""Thin wrapper over oracledb that mirrors the notebook's §3.1 `connect()` helper."""

import oracledb
from config import (
    AGENT_USER, AGENT_PASS,
    DEMO_USER, DEMO_PASS,
    SYS_USER, SYS_PASS, SYS_DSN,
)


def connect(user: str, password: str, dsn: str = SYS_DSN, mode: int | None = None):
    """Create a thin-mode oracledb connection. `mode` only used for SYSDBA."""
    kwargs = {"user": user, "password": password, "dsn": dsn}
    if mode is not None:
        kwargs["mode"] = mode
    return oracledb.connect(**kwargs)


def connect_sys():
    return connect(SYS_USER, SYS_PASS, SYS_DSN, mode=oracledb.AUTH_MODE_SYSDBA)


def connect_agent():
    return connect(AGENT_USER, AGENT_PASS, SYS_DSN)


def connect_demo():
    return connect(DEMO_USER, DEMO_PASS, SYS_DSN)
