"""SQLcl-tee: capture every SQL the agent runs as a human-readable log.

WHY THIS EXISTS
---------------
The MCP layer shows the SQL the *agent* emits (the parameter values it
chose). SQLcl shows the result the *database* actually produced (rows,
errors, execution plan). Pairing the two gives us a complete trace of one
agent turn — useful for debugging, demos, and post-mortem analysis.

SQLcl install (Ubuntu 24.04): see `shared/references/sqlcl-tee.md`. This
snippet assumes `sql` is on PATH (or in `~/opt/sqlcl/bin/`).

The tee is opinionated: best-effort, never blocks the agent's response.
If SQLcl isn't installed, the wrapper logs a one-line warning and
returns the underlying tool's result untouched.

USAGE
-----
The intermediate / advanced tier skills wrap the `run_sql` BaseTool with
this teer:

    from .sqlcl_tee import wrap_with_sqlcl_tee
    run_sql = wrap_with_sqlcl_tee(run_sql, sql_dir="sql/", log_dir="logs/")
"""

from __future__ import annotations

import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

from langchain_core.tools import BaseTool
from pydantic import Field


def _sqlcl_path() -> str | None:
    """Return absolute path to `sql` (SQLcl), or None if not installed."""
    p = shutil.which("sql")
    if p:
        return p
    fallback = Path.home() / "opt" / "sqlcl" / "bin" / "sql"
    if fallback.exists():
        return str(fallback)
    return None


class TeedRunSQL(BaseTool):
    """Subclass `BaseTool` (not monkeypatch — Pydantic 2 forbids that, see
    friction P1-8). Wraps an inner `run_sql` BaseTool, tees the SQL through
    SQLcl in the background, and appends `[sqlcl_log: <path>]` to the inner
    tool's result so the caller can read it back."""

    name: str = "run_sql"
    description: str = ""
    inner_tool: Any = Field(exclude=True)
    sql_dir: str = "sql"
    log_dir: str = "logs"

    class Config:
        arbitrary_types_allowed = True

    def __init__(self, inner_tool: BaseTool, sql_dir: str = "sql", log_dir: str = "logs"):
        super().__init__(
            name=inner_tool.name,
            description=inner_tool.description,
            inner_tool=inner_tool,
            sql_dir=sql_dir,
            log_dir=log_dir,
        )
        Path(self.sql_dir).mkdir(parents=True, exist_ok=True)
        Path(self.log_dir).mkdir(parents=True, exist_ok=True)

    def _run(self, *args, **kwargs) -> str:  # type: ignore[override]
        # Inner tool result is the source of truth — tee is best-effort.
        result = self.inner_tool.invoke(kwargs if kwargs else (args[0] if args else {}))

        sql_text = kwargs.get("sql") or kwargs.get("query") or ""
        if not isinstance(sql_text, str) or not sql_text.strip():
            return str(result)

        sqlcl = _sqlcl_path()
        if sqlcl is None:
            return f"{result}\n[sqlcl_tee: skipped — SQLcl not installed]"

        ts = int(time.time())
        sql_path = Path(self.sql_dir) / f"run_{ts}.sql"
        log_path = Path(self.log_dir) / f"sqlcl_{ts}.log"

        sql_path.write_text(sql_text + (";\n" if not sql_text.rstrip().endswith(";") else "\n"))

        dsn = (
            f"{os.environ['DB_USER']}/{os.environ['DB_PASSWORD']}"
            f"@{os.environ['DB_DSN']}"
        )
        with open(log_path, "wb") as logf:
            subprocess.Popen(
                [sqlcl, "-L", "-S", dsn, f"@{sql_path}"],
                stdout=logf,
                stderr=subprocess.STDOUT,
                close_fds=True,
            )

        return f"{result}\n[sqlcl_log: {log_path}]"


def wrap_with_sqlcl_tee(
    inner_tool: BaseTool,
    sql_dir: str = "sql",
    log_dir: str = "logs",
) -> BaseTool:
    """Convenience: turn an existing `run_sql` BaseTool into a teed one."""
    return TeedRunSQL(inner_tool=inner_tool, sql_dir=sql_dir, log_dir=log_dir)
