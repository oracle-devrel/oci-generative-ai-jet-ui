"""Oracle SQL / PL/SQL file runner.

WHY THIS EXISTS
---------------
Migration files mix plain DDL/DML (terminated by `;`) with PL/SQL blocks
(terminated by `/` on its own line). A naïve `script.split(';')` corrupts
PL/SQL:

    BEGIN
      FOR r IN (SELECT id FROM t) LOOP        -- the ; here is INSIDE a block
        DBMS_OUTPUT.PUT_LINE(r.id);
      END LOOP;
    END;
    /

The intermediate v3 cold-start walk discovered every implementer ends up
hand-rolling this splitter. They all break on `BEGIN…END;/` blocks. This
module is the canonical version (v3 friction P1-V3-F-2).

USAGE
-----
    from <package_slug>.sql_runner import run_sql_file
    with oracledb.connect(...) as conn:
        run_sql_file(conn, "migrations/001_schema.sql")

It runs each statement in order, COMMITs on the connection at the end,
and re-raises the first error with the offending statement preserved
in the exception's `__notes__` for easy debugging.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable


_PLSQL_BLOCK_OPENERS = re.compile(
    r"^\s*(DECLARE|BEGIN|CREATE\s+(OR\s+REPLACE\s+)?"
    r"(PROCEDURE|FUNCTION|PACKAGE|TRIGGER|TYPE\s+BODY))\b",
    re.IGNORECASE,
)


def split_oracle_script(script: str) -> list[str]:
    """Split an Oracle script into individually-runnable statements.

    Rules:
    - A line containing only `/` (whitespace allowed) closes a PL/SQL block.
    - Statements not starting with a PL/SQL opener are split on `;` at the
      end of a logical line — the `;` itself is consumed.
    - Comments (`--` to EOL, and `/* ... */`) are stripped before splitting
      so a `;` inside a comment doesn't break the parse. Comments inside a
      PL/SQL block are preserved (the DB tolerates them).
    """
    # Strip /* ... */ block comments (non-greedy, multiline).
    no_block_comments = re.sub(r"/\*.*?\*/", "", script, flags=re.DOTALL)
    lines = no_block_comments.splitlines()

    statements: list[str] = []
    buf: list[str] = []
    in_plsql = False

    def flush():
        s = "\n".join(buf).strip().rstrip(";").strip()
        if s:
            statements.append(s)
        buf.clear()

    for raw in lines:
        line = raw
        # Drop -- to EOL comments only outside strings. Cheap heuristic:
        # if the line is unambiguously a comment, drop it; otherwise keep
        # it (Oracle tolerates inline comments inside statements).
        stripped = line.strip()
        if stripped.startswith("--"):
            continue

        # `/` on its own line closes a PL/SQL block.
        if stripped == "/":
            if buf:
                statements.append("\n".join(buf).strip())
                buf.clear()
            in_plsql = False
            continue

        # If buf is empty-or-blank AND this line opens a PL/SQL block, flip.
        # Using "first non-blank line in (buf+[line])" instead of "not buf" so
        # blank lines from prior whitespace don't mask the opener detection.
        if not in_plsql:
            head = next((s for s in (*buf, line) if s.strip()), "")
            if _PLSQL_BLOCK_OPENERS.match(head):
                in_plsql = True

        buf.append(line)

        # Outside PL/SQL: split on lines that end with `;`.
        if not in_plsql and stripped.endswith(";"):
            flush()

    # Trailing remainder (file without final `/` or `;`).
    if buf:
        flush()

    return [s for s in statements if s.strip()]


def run_sql_file(conn, path: str | Path, *, commit: bool = True) -> int:
    """Execute every statement in `path` against `conn`. Returns count run.

    On error, the offending statement is attached to the exception via
    `__notes__` (Python 3.11+) so logs make the failure obvious.
    """
    text = Path(path).read_text(encoding="utf-8")
    statements = split_oracle_script(text)
    return run_statements(conn, statements, commit=commit, source=str(path))


def run_statements(
    conn,
    statements: Iterable[str],
    *,
    commit: bool = True,
    source: str = "<inline>",
) -> int:
    """Run a sequence of pre-split statements. Returns count run."""
    count = 0
    with conn.cursor() as cur:
        for i, stmt in enumerate(statements, start=1):
            try:
                cur.execute(stmt)
                count += 1
            except Exception as e:
                # Python 3.11+: attach context without obscuring the original.
                if hasattr(e, "add_note"):
                    e.add_note(f"[sql_runner] {source} statement {i}:\n{stmt}")
                raise
    if commit:
        conn.commit()
    return count


# ─── INSERT ... RETURNING — separate, because it needs an OUT bind ───────────
#
# v3 friction P1-V3-N7: `cur.execute("INSERT ... RETURNING id INTO :out", ...)`
# followed by `cur.fetchone()` raises `DPY-1003: an output variable was not
# supplied for an OUT bind variable` in oracledb >= 2.x. The fix is to bind a
# `cur.var(...)` for the OUT slot and read it back via `getvalue()`.
#
# Use this helper instead of writing the INSERT...RETURNING idiom by hand.
def insert_returning_id(
    conn,
    table: str,
    columns: dict[str, object],
    id_column: str = "id",
    *,
    commit: bool = False,
):
    """INSERT a row into `table`, return the autogenerated `id_column` value.

    Example:
        new_id = insert_returning_id(
            conn, "ORDERS",
            {"customer_id": 86, "total": 199.99, "status": "OPEN"},
        )
    """
    import oracledb

    cols = list(columns.keys())
    placeholders = [f":{c}" for c in cols]
    binds = dict(columns)
    sql = (
        f"INSERT INTO {table} ({', '.join(cols)}) "
        f"VALUES ({', '.join(placeholders)}) "
        f"RETURNING {id_column} INTO :out_id"
    )
    with conn.cursor() as cur:
        out_var = cur.var(oracledb.NUMBER)
        binds["out_id"] = out_var
        cur.execute(sql, binds)
        result = out_var.getvalue()
        if isinstance(result, list):  # oracledb returns a list-of-1 here
            result = result[0] if result else None
    if commit:
        conn.commit()
    return result
