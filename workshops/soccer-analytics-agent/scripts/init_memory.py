#!/usr/bin/env python3
"""Apply memory schema.sql to the soccer schema."""

from pathlib import Path

from soccer_agent.db import get_connection
from soccer_agent.observability.langgraph_steps import ensure_observability_store

REPO = Path(__file__).resolve().parent.parent
SCHEMA = REPO / "soccer_agent" / "memory" / "schema.sql"


def _split_statements(sql: str) -> list[str]:
    stmts, buf = [], []
    for line in sql.splitlines():
        if line.strip().startswith("--") or not line.strip():
            continue
        buf.append(line)
        if line.rstrip().endswith(";"):
            stmts.append("\n".join(buf).rstrip(";\n"))
            buf = []
    return stmts


def main() -> None:
    sql = SCHEMA.read_text()
    with get_connection() as conn:
        cur = conn.cursor()
        # Drop in dependency order before recreate (idempotent).
        for t in ["EPISODIC_MEMORY", "SEMANTIC_MEMORY",
                  "WORKING_MEMORY", "AGENT_SESSIONS"]:
            try:
                cur.execute(f"DROP TABLE {t} CASCADE CONSTRAINTS")
            except Exception:
                pass
        for stmt in _split_statements(sql):
            cur.execute(stmt)
        conn.commit()
    print("Memory schema applied.")
    ensure_observability_store()
    print("LangGraph OracleDB observability store applied.")


if __name__ == "__main__":
    main()
