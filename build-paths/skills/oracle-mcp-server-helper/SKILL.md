---
name: oracle-mcp-server-helper
description: Wire the oracle-database-mcp-server into a Python project so an LLM agent can call list_tables / describe_table / run_sql / vector_search at inference time. Handles install, stdio launch, and LangChain tool conversion via langchain-mcp-adapters. Use whenever a project needs a Grok 4 / GPT-class agent that talks to a live Oracle schema.
inputs:
  - target_dir: project root (must already have a working DB and store layer)
  - package_slug: snake_case Python package name
  - allowed_tools: subset of {list_tables, describe_table, describe_schema, run_sql, vector_search} — default = all
  - sql_mode: "read_only" (default) or "read_write" — read_write enables INSERT/UPDATE/DELETE/DDL
  - tool_prefix: optional namespace for emitted LangChain tools (default = "oracle_")
outputs:
  - target_dir/src/<package_slug>/mcp_client.py    (server launcher + LangChain tool factory)
  - target_dir/src/<package_slug>/tool_registry.py (cached list[BaseTool] for the agent loop)
  - additions to target_dir/pyproject.toml
  - additions to target_dir/.env
---

You wire MCP. You do not write the agent loop, the chain, or the UI — those are tier-skill responsibilities.

## Step 0 — References

- `shared/references/sources.md` — links to oracle-database-mcp-server.
- `shared/references/oracledb-python.md` — `oracledb.connect()` shape.
- `shared/references/langchain-oracledb.md` — vector_search semantics if exposed.

## Step 1 — Validate inputs

- `target_dir/.env` has `DB_DSN`, `DB_USER`, `DB_PASSWORD`.
- A working `store.py` exists at `target_dir/src/<package_slug>/store.py` (langchain-oracledb-helper output). If not, stop — order matters.
- `sql_mode == "read_write"` requires the user to confirm explicitly during interview. Refuse to proceed silently — destructive SQL via an LLM agent is a footgun.

> Several directives below are adapted from Oracle's official SQLcl MCP skill (`oracle/skills` · `db/sqlcl/sqlcl-mcp-server.md`). Kept as guidance, not code-path swaps.

### If SQLcl 25.2+ is on PATH

`sql -mcp` (Oracle's first-party MCP server) ships in SQLcl 25.2 and later. Detect with `sql -V`. When present, the workshop attendee has the *option* of swapping our local-tool layer for the SQLcl transport — surface this as a note in the project README, do not auto-switch. Tool surface aligns 1:1 on `list_tables`, `describe_table`, `run_sql`; SQLcl exposes `run-sqlcl` (DDL/LOAD/Liquibase) which is out of scope for this scaffold; SQLcl does NOT expose `vector_search`, so our local `VectorSearchTool` stays project-local in either transport. Restrict levels (`-R 0..4`) and the `-savepwd` connection store are SQLcl-only and not replicated here.

### Recommended DB user shape

Workshop attendees default to running as the schema owner. Recommend (don't enforce) a least-privilege user instead — same posture as SQLcl's `mcp_reader` example:

```sql
CREATE USER cyp_mcp IDENTIFIED BY "<strong>";
GRANT CREATE SESSION TO cyp_mcp;
GRANT SELECT ANY DICTIONARY TO cyp_mcp;            -- schema introspection
GRANT SELECT ON owner.your_table TO cyp_mcp;       -- per-table reads
-- For the advanced schema-designer idea (sql_mode=read_write) only:
-- GRANT CREATE TABLE, CREATE VIEW TO cyp_mcp;
```

Surface this in the project README. Don't run the DDL automatically — the user should pick when to harden their setup.

## Step 2 — Add deps

> **Friction P0-1:** the previous version of this skill named `oracle-database-mcp-server` as a pip dependency. That package does NOT exist on PyPI. Until a canonical Oracle MCP server is published, this skill scaffolds a **local in-process tool layer** that exposes the same surface (`list_tables`, `describe_table`, `run_sql`, `vector_search`) as `langchain_core.tools.BaseTool` subclasses calling `oracledb.Cursor` directly. The agent gets the same typed contract — there's just no out-of-process MCP server.

In `target_dir/pyproject.toml` under `[project] dependencies`:

```
"oracledb>=2.5",
"langchain-core>=0.3",
"langchain-community>=0.3",
```

Run `pip install -e .` from `target_dir`. If the user's environment is conda, prefer absolute paths (`~/miniconda3/envs/<env>/bin/pip install -e .`) — `conda activate` does not work in non-interactive bash.

## Step 3 — Add env keys

Append to `target_dir/.env.example` (and `.env` if it exists):

```
# Oracle MCP server — connection inherited from DB_DSN/DB_USER/DB_PASSWORD
ORACLE_MCP_SQL_MODE=<read_only|read_write>
ORACLE_MCP_ALLOWED_TOOLS=<comma-separated allowed_tools>
```

## Step 4 — Write `mcp_client.py` (local-tool scaffold)

Implement four LangChain `BaseTool` subclasses calling `oracledb` directly. Use **subclasses** (not monkeypatched instances — Pydantic 2 forbids that, friction P1-8).

```python
"""
Oracle local-tool scaffold (substitute for an out-of-process MCP server until
oracle-database-mcp-server is published on PyPI; see friction P0-1).

Each tool is a LangChain BaseTool subclass calling oracledb.Cursor directly.
Same surface as the eventual MCP server — list_tables, describe_table,
run_sql, vector_search — so swapping in a real MCP server later is mechanical.

Cites:
- shared/references/sources.md
- shared/references/langchain-oracledb.md
"""
import os
from typing import Any, List

import oracledb
from langchain_core.tools import BaseTool
from pydantic import Field

from .store import get_connection, get_store  # from langchain-oracledb-helper


def _readonly_mode() -> bool:
    return os.environ.get("ORACLE_MCP_SQL_MODE", "read_only") == "read_only"


class ListTablesTool(BaseTool):
    name: str = "list_tables"
    description: str = (
        "List user-owned tables in the connected Oracle schema. "
        "No arguments. Returns a JSON list of table names."
    )

    def _run(self) -> str:  # type: ignore[override]
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT table_name FROM USER_TABLES ORDER BY table_name"
            )
            rows = [r[0] for r in cur.fetchall()]
        return repr(rows)


class DescribeTableTool(BaseTool):
    name: str = "describe_table"
    description: str = (
        "Describe one table's columns. Args: table_name (str). "
        "Returns a JSON list of {column_name, data_type, nullable}."
    )

    def _run(self, table_name: str) -> str:  # type: ignore[override]
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT column_name, data_type, nullable "
                "FROM USER_TAB_COLUMNS WHERE table_name = :t "
                "ORDER BY column_id",
                t=table_name.upper(),
            )
            cols = [
                {"column_name": c[0], "data_type": c[1], "nullable": c[2]}
                for c in cur.fetchall()
            ]
        return repr(cols)


class RunSQLTool(BaseTool):
    name: str = "run_sql"
    description: str = (
        "Execute a SQL statement and return rows as a JSON list. "
        "Args: sql (str). In read_only mode (default) only SELECT and "
        "WITH ... SELECT statements are allowed; mutating SQL is rejected."
    )

    def _run(self, sql: str) -> str:  # type: ignore[override]
        # Strip leading SQL comments + whitespace before keyword-matching, so
        # `/* foo */ DROP TABLE x` can't slip past a startswith() check.
        stripped = sql.lstrip()
        while stripped.startswith("--") or stripped.startswith("/*"):
            if stripped.startswith("--"):
                _, _, stripped = stripped.partition("\n")
            else:
                _, _, stripped = stripped.partition("*/")
            stripped = stripped.lstrip()
        first = stripped.lower().split(None, 1)[0] if stripped else ""

        if _readonly_mode():
            # Allow only true read shapes. EXPLAIN can mutate via PLAN_TABLE side
            # effects; CALL / BEGIN / DECLARE can wrap arbitrary PL/SQL — reject.
            if first not in ("select", "with"):
                return (
                    "[run_sql refused — read_only mode rejects mutating SQL "
                    f"(leading keyword: {first!r}). "
                    "Set ORACLE_MCP_SQL_MODE=read_write to enable.]"
                )

        # AWR / V$SQL traceability — same shape SQLcl's MCP server uses natively.
        # Lets a DBA grep V$SQL for agent-issued statements.
        model = os.environ.get("CYP_LLM_MODEL", "grok-4")
        tagged_sql = f"/* LLM in use is {model} */ {sql}"

        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute(tagged_sql)
            cols = [d[0] for d in cur.description] if cur.description else []
            rows = cur.fetchall() if cols else []
        return repr({"columns": cols, "rows": [list(r) for r in rows]})


class VectorSearchTool(BaseTool):
    name: str = "vector_search"
    description: str = (
        "Similarity search over a registered OracleVS collection. "
        "Args: collection (str — one of the project's configured collections), "
        "query (str), k (int, default 5). Returns the top-k chunks with metadata."
    )

    def _run(  # type: ignore[override]
        self, collection: str, query: str, k: int = 5
    ) -> str:
        store = get_store(collection)
        hits = store.similarity_search(query, k=k)
        return repr(
            [
                {"page_content": h.page_content, "metadata": h.metadata}
                for h in hits
            ]
        )


def list_tools() -> List[BaseTool]:
    """Return the per-project subset of allowed tools."""
    allowed = set(
        s.strip()
        for s in os.environ.get(
            "ORACLE_MCP_ALLOWED_TOOLS",
            "list_tables,describe_table,run_sql,vector_search",
        ).split(",")
        if s.strip()
    )
    catalog = {
        "list_tables": ListTablesTool(),
        "describe_table": DescribeTableTool(),
        "run_sql": RunSQLTool(),
        "vector_search": VectorSearchTool(),
    }
    return [catalog[name] for name in catalog if name in allowed]
```

Notes for the tier skill that uses this:
- Tools come back as `langchain_core.tools.BaseTool` subclasses. Bind them to the LLM via `llm.bind_tools(list_tools())` — no manual `@tool` decoration needed.
- Wrap `RunSQLTool` with `shared/snippets/sqlcl_tee.py` if you want a SQLcl-tee log per query (intermediate tier folds this in by default).
- When a real `oracle-database-mcp-server` appears on PyPI, swap `list_tools()`'s body for an MCP-stdio session; the tool surface is unchanged so callers don't break.

**Friction P1-render-cell (run-3):** If your tier rewrites `RunSQLTool._run` to format rows as **tab-separated text** (intermediate / advanced both do this for human-readable demo output) instead of the snippet's `repr({"columns": ..., "rows": ...})` shape, the snippet does NOT ship a per-cell renderer. Two failure modes if you forget:
1. `NameError: name '_render_cell' is not defined` on every `run_sql` call (intermediate-nl2sql included the helper; advanced-hybrid-analyst dropped it during the clone — every data-route question failed end-to-end until added).
2. CLOB/BLOB columns render as `<oracledb.LOB object at 0x…>` because `str(<lob>)` doesn't materialize the value.

Either keep the snippet's JSON-repr return shape, or paste this stanza immediately above your `RunSQLTool`:

```python
def _render_cell(value) -> str:
    if value is None:
        return ""
    if hasattr(value, "read"):
        try:
            value = value.read()
        except Exception:
            return repr(value)
    if isinstance(value, (bytes, bytearray)):
        try:
            value = value.decode("utf-8", errors="replace")
        except Exception:
            return repr(value)
    text = str(value).replace("\t", " ").replace("\n", " ")
    return text if len(text) <= 200 else text[:200] + "…"
```

## Step 4.5 — Tag agent sessions in V$SESSION

Add two lines to `langchain-oracledb-helper`'s `get_connection()` so DBAs can spot agent-issued sessions in real time (`SELECT module, action FROM v$session`). Adapted from SQLcl's MCP server, which sets these natively:

```python
import os
# inside get_connection(), after oracledb.connect(...):
with conn.cursor() as cur:
    cur.callproc(
        "dbms_application_info.set_module",
        [os.environ.get("CYP_MCP_CLIENT", "cyp-agent"),
         os.environ.get("CYP_LLM_MODEL", "grok-4")],
    )
```

If `langchain-oracledb-helper` already shipped `get_connection()`, add this in `target_dir/src/<package_slug>/store.py` next to the existing `oracledb.connect(...)` call rather than monkeypatching.

## Step 4.6 — Optional CYP_MCP_LOG audit table

Same shape as SQLcl's `DBTOOLS$MCP_LOG`, but works for the local-tool transport. Scaffold this only if the tier skill or the user asks for it (the advanced tier's idea-3 schema designer is the obvious candidate). Skip by default for tier-2 demos.

```sql
-- One-time DDL, runs on first connection if missing:
CREATE TABLE IF NOT EXISTS CYP_MCP_LOG (
  id           NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  ts           TIMESTAMP DEFAULT SYSTIMESTAMP,
  mcp_client   VARCHAR2(100),
  model        VARCHAR2(100),
  tool_name    VARCHAR2(100),
  log_message  CLOB
);
```

Then in `RunSQLTool._run`, after `cur.execute(tagged_sql)`, insert one row per call:

```python
cur.execute(
    "INSERT INTO CYP_MCP_LOG (mcp_client, model, tool_name, log_message) "
    "VALUES (:c, :m, :t, :l)",
    c=os.environ.get("CYP_MCP_CLIENT", "cyp-agent"),
    m=os.environ.get("CYP_LLM_MODEL", "grok-4"),
    t="run_sql",
    l=sql[:4000],
)
conn.commit()
```

Gives the workshop attendee a real audit trail without the SQLcl dependency. ~15 LOC. When transport later switches to `sql -mcp`, drop this table — `DBTOOLS$MCP_LOG` takes over.

## Step 5 — Write `tool_registry.py`

```python
"""
Cached list of available MCP tools for the agent.

Why a registry: building the tool list spawns a subprocess. Cache it once
per process so the agent loop doesn't pay that cost per turn.
"""
from functools import lru_cache
from typing import List
from langchain_core.tools import BaseTool

from .mcp_client import list_tools


@lru_cache(maxsize=1)
def get_tools() -> List[BaseTool]:
    return list_tools()


def get_tool(name: str) -> BaseTool:
    for t in get_tools():
        if t.name == name:
            return t
    raise KeyError(f"no MCP tool named {name!r}")
```

## Step 6 — Smoke

```python
from <package_slug>.tool_registry import get_tools

tools = get_tools()
names = [t.name for t in tools]
print(f"oracle-mcp-server-helper: OK (tools: {', '.join(names)})")

# call list_tables to prove the server actually works
list_tables = next(t for t in tools if "list_tables" in t.name)
result = list_tables.invoke({})
print(f"  found {len(result)} tables")
```

If the smoke hangs > 30s, the MCP server didn't initialize — usually because `DB_DSN` is wrong or the container isn't healthy. Stop and report.

## Stop conditions

- `oracle-database-mcp-server` binary not on PATH after `pip install -e .`. Show the install path and stop.
- `sql_mode=read_write` without explicit user confirmation. Refuse.
- The MCP server fails to initialize within 30s. Print the stderr from the subprocess and stop.

## What you must NOT do

- Don't expose `run_sql` in `read_write` mode without surfacing the risk in the tier README.
- Don't share one MCP session across processes (Gunicorn workers, etc.) — each process spawns its own. Document this.
- Don't convert MCP tools manually. Use `load_mcp_tools` — it preserves the JSON schema for tool calls.

## Final report

```
oracle-mcp-server-helper: OK
  client:    target_dir/src/<package_slug>/mcp_client.py
  registry:  target_dir/src/<package_slug>/tool_registry.py
  tools:     <comma list of tool names>
  sql_mode:  <read_only|read_write>
  next:      hand off to the tier skill — it builds the agent loop using these tools.
```
