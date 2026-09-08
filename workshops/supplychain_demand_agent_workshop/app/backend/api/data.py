"""Data Explorer endpoints — read-only views over the Oracle tables the
workshop creates. Surfaced to the frontend as `/api/tables` and
`/api/tables/{name}/rows`.
"""

from __future__ import annotations

import logging
from typing import Any

from app.backend.db.connections import sync_client
from fastapi import APIRouter, HTTPException, Query

log = logging.getLogger("app.api.data")
router = APIRouter()


# ─── The tables we expose ────────────────────────────────────────────────
# Each entry: (display name in upper-case, schema we expect to find,
#              short purpose blurb, color tag for the UI).
DEMO_TABLES = [
    {
        "id": "SUPPLYCHAIN_DEMAND",
        "label": "supplychain_demand",
        "purpose": "OracleVS — demand reports + policy memo (LangChain vector store)",
        "kind": "vector",
    },
    {
        "id": "LANGCHAIN_DEMAND_CACHE",
        "label": "langchain_demand_cache",
        "purpose": "OracleSemanticCache — cached LLM prompts/responses",
        "kind": "cache",
    },
    {
        "id": "LANGCHAIN_PLANNER_CHAT",
        "label": "langchain_planner_chat",
        "purpose": "OracleChatMessageHistory — chat-session transcripts",
        "kind": "chat",
    },
    {
        "id": "STORE_AGENT_MEMORY",
        "label": "store_agent_memory",
        "purpose": "AsyncOracleStore — long-term cross-thread memory (user prefs)",
        "kind": "store",
    },
    {
        "id": "STORE_VECTORS_AGENT_MEMORY",
        "label": "store_vectors_agent_memory",
        "purpose": "AsyncOracleStore — vector index for the long-term store",
        "kind": "store",
    },
    {
        "id": "CHECKPOINTS",
        "label": "checkpoints",
        "purpose": "AsyncOracleSaver — per-thread agent checkpoint heads",
        "kind": "checkpoint",
    },
    {
        "id": "CHECKPOINT_WRITES",
        "label": "checkpoint_writes",
        "purpose": "AsyncOracleSaver — channel writes per checkpoint",
        "kind": "checkpoint",
    },
    {
        "id": "CHECKPOINT_BLOBS",
        "label": "checkpoint_blobs",
        "purpose": "AsyncOracleSaver — serialized channel values",
        "kind": "checkpoint",
    },
]


# ─── Helpers ─────────────────────────────────────────────────────────────
def _resolve_table_name(cur, requested: str) -> str | None:
    """Find the case-preserved name Oracle actually stored.

    `langchain_oracledb` creates tables with quoted lowercase identifiers
    (`"supplychain_demand"`), while `langgraph-oracledb` and Oracle's own
    DDL create them upper-case (`CHECKPOINTS`). We do a case-insensitive
    lookup so the rest of the code uses whatever Oracle actually has.
    """
    cur.execute(
        "SELECT table_name FROM user_tables WHERE UPPER(table_name) = :n",
        n=requested.upper(),
    )
    row = cur.fetchone()
    return row[0] if row else None


def _row_count(cur, table: str) -> int | None:
    """Count rows in a table whose stored name is `table` (case-preserved)."""
    try:
        cur.execute(f'SELECT COUNT(*) FROM "{table}"')
        (n,) = cur.fetchone()
        return int(n)
    except Exception:
        return None


def _columns_for(cur, table: str) -> list[dict[str, Any]]:
    """Pull the column list for the case-preserved `table` name."""
    cur.execute(
        """
        SELECT column_name, data_type, data_length, nullable
          FROM user_tab_columns
         WHERE table_name = :t
         ORDER BY column_id
        """,
        t=table,
    )
    return [
        {"name": name, "type": dtype, "length": length, "nullable": nullable == "Y"}
        for (name, dtype, length, nullable) in cur.fetchall()
    ]


def _readable_cell(value: Any) -> Any:
    """Coerce Oracle cell types into something JSON-serialisable + UI-friendly."""
    if value is None:
        return None
    if isinstance(value, str | int | float | bool):
        return value
    # bytes / LOBs / vectors: render as a short stringified preview
    try:
        if hasattr(value, "read"):  # LOB
            try:
                raw = value.read()
            except Exception:
                return f"<{type(value).__name__}>"
            if isinstance(raw, bytes):
                return f"<{len(raw)} bytes>"
            return str(raw)[:1000]
        if isinstance(value, bytes):
            return f"<{len(value)} bytes>"
    except Exception:
        return repr(value)[:200]
    # everything else (datetime, array, etc.)
    return str(value)[:1000]


# ─── Endpoints ───────────────────────────────────────────────────────────
@router.get("/api/tables")
def list_tables() -> dict:
    """Return the demo-table catalogue with current row counts."""
    client = sync_client()
    cur = client.cursor()
    out: list[dict[str, Any]] = []
    for spec in DEMO_TABLES:
        entry = dict(spec)
        actual = _resolve_table_name(cur, spec["id"])
        entry["exists"] = actual is not None
        entry["row_count"] = _row_count(cur, actual) if actual else None
        out.append(entry)
    return {"tables": out}


@router.get("/api/tables/{table_name}/rows")
def table_rows(
    table_name: str,
    limit: int = Query(50, ge=1, le=500),
    search: str | None = Query(None, description="case-insensitive substring filter"),
) -> dict:
    """Return up to `limit` rows from a known table, plus column metadata."""
    # Hard-guard against arbitrary table access.
    allowed = {spec["id"] for spec in DEMO_TABLES}
    upper = table_name.upper()
    if upper not in allowed:
        raise HTTPException(status_code=404, detail=f"table {table_name!r} not in demo set")

    client = sync_client()
    cur = client.cursor()
    actual = _resolve_table_name(cur, upper)
    if actual is None:
        raise HTTPException(status_code=404, detail=f"table {table_name!r} does not exist")

    columns = _columns_for(cur, actual)
    if not columns:
        raise HTTPException(status_code=404, detail=f"table {table_name!r} has no columns")

    select_cols = ", ".join(f'"{c["name"]}"' for c in columns)
    cur.execute(f'SELECT {select_cols} FROM "{actual}" FETCH FIRST :n ROWS ONLY', n=limit)
    rows_raw = cur.fetchall()

    rows: list[list[Any]] = []
    for r in rows_raw:
        rows.append([_readable_cell(v) for v in r])

    if search:
        s = search.lower()
        rows = [row for row in rows if any(s in str(v).lower() for v in row if v is not None)]

    total = _row_count(cur, actual)
    return {
        "table": actual,
        "columns": columns,
        "rows": rows,
        "row_count_total": total,
        "row_count_shown": len(rows),
        "limit": limit,
        "search": search,
    }
