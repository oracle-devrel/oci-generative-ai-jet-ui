"""REST endpoints for the Data Explorer bottom pane.

Exposes a small allowlist of tables in SUPPLYCHAIN + AGENT so the front-end can
browse rows without leaving the app. Schema/table names are validated against the
allowlist; columns are introspected via cursor.description, and SDO_GEOMETRY +
LOB values are rendered as compact strings rather than raw Python objects.
"""

from __future__ import annotations

import array
import datetime
import traceback
from typing import Any

import oracledb
from flask import Blueprint, jsonify, request

from api.identities import (
    column_is_masked,
    get_identity,
    is_table_forbidden,
    list_identities,
    region_filter_clause,
)
from config import AGENT_USER, DEMO_USER


data_bp = Blueprint("data", __name__)


# Schema → ordered list of tables we want exposed in the explorer.
# DEMO_USER resolves to "SUPPLYCHAIN" by default (the supply-chain schema);
# anything from a legacy DEMO schema is intentionally not surfaced here.
TABLE_ALLOWLIST: dict[str, list[str]] = {
    DEMO_USER.upper(): [
        "CARRIERS", "VESSELS", "PORTS", "VOYAGES",
        "VESSEL_POSITIONS", "CONTAINERS", "CARGO_ITEMS",
    ],
    AGENT_USER.upper(): [
        "TOOLBOX", "SKILLBOX", "SCHEMA_ACL", "AGENT_AUTHORIZATIONS",
        "AGENT_CLEARANCES", "SCAN_HISTORY",
    ],
}


# Columns we'll skip from the SELECT entirely — vectors are too large to
# render in the grid and aren't useful as text.
SKIP_COLUMN_TYPES = {"VECTOR"}


_state: dict = {}


def init_data_routes(*, agent_conn, memory_client):
    _state["agent_conn"] = agent_conn
    _state["memory_client"] = memory_client


def _safe_table_name(schema: str, table: str) -> str | None:
    """Return f'{schema}.{table}' if both are in the allowlist, else None."""
    s, t = schema.upper(), table.upper()
    if s not in TABLE_ALLOWLIST or t not in TABLE_ALLOWLIST[s]:
        return None
    return f"{s}.{t}"


def _render_value(v: Any) -> Any:
    """Convert oracledb value to a JSON-serializable representation.

    Has to handle the full menagerie: None, primitives, datetimes, bytes, LOBs,
    SDO_GEOMETRY DbObjects, VECTOR columns (which arrive as array.array), JSON
    columns (already dicts/lists), and any other DbObject we might see.
    """
    if v is None:
        return None
    if hasattr(v, "read"):  # CLOB/BLOB
        try:
            data = v.read()
            if isinstance(data, bytes):
                return f"[BLOB {len(data)} bytes]"
            return data[:2000]
        except Exception:
            return "[LOB read failed]"
    # VECTOR columns come back as array.array
    if isinstance(v, array.array):
        return f"[VECTOR {len(v)}-dim]"
    # SDO_GEOMETRY (and other DbObjects)
    if isinstance(v, oracledb.DbObject):
        try:
            if hasattr(v, "SDO_POINT") and v.SDO_POINT is not None:
                pt = v.SDO_POINT
                return f"POINT({pt.X:.4f}, {pt.Y:.4f})"
        except Exception:
            pass
        try:
            return f"[{v.type.name}]"
        except Exception:
            return "[OBJECT]"
    if isinstance(v, (datetime.datetime, datetime.date)):
        return v.isoformat()
    if isinstance(v, bytes):
        return f"[BYTES {len(v)}]"
    # Primitives the JSON encoder handles natively
    if isinstance(v, (str, int, float, bool, list, dict)):
        return v
    # Unknown — fall back to str so jsonify never raises
    return str(v)


@data_bp.route("/api/data/tables", methods=["GET"])
def list_tables():
    """List every allow-listed table with its current row count.
    Also includes a synthetic 'DBFS.scratchpad' entry that surfaces the DBFS
    file system in the same grid as the SQL tables.

    Honors the `as_user` query param to flag tables forbidden to the chosen
    identity — they still show in the tab strip but the row fetch will refuse
    them with a 403.
    """
    conn = _state.get("agent_conn")
    if not conn:
        return jsonify({"error": "not initialized"}), 503

    identity = get_identity(request.args.get("as_user"))
    out = []

    # Synthetic: DBFS scratchpad as a "table"
    try:
        from db.dbfs import DBFS
        scratch = DBFS(conn)
        files = scratch.list("/")
        out.append({"schema": "DBFS", "name": "scratchpad",
                    "row_count": len(files), "forbidden": False})
    except Exception:
        out.append({"schema": "DBFS", "name": "scratchpad",
                    "row_count": None, "forbidden": False})

    with conn.cursor() as cur:
        for schema, tables in TABLE_ALLOWLIST.items():
            for table in tables:
                qualified = f"{schema}.{table}"
                try:
                    cur.execute(f"SELECT COUNT(*) FROM {qualified}")
                    n = cur.fetchone()[0]
                except oracledb.DatabaseError:
                    n = None
                out.append({
                    "schema": schema, "name": table, "row_count": n,
                    "forbidden": is_table_forbidden(identity, schema, table),
                })
    return jsonify({"tables": out, "identity": identity.as_json()})


@data_bp.route("/api/identities", methods=["GET"])
def get_identities():
    """Return every identity the user can switch to, in display order.

    These are application-layer personas the front-end's "Use As:" selector
    surfaces. Each one carries a clearance, an optional region restriction, a
    list of masked columns, and a list of forbidden tables — exactly the same
    shape DDS / DBMS_RLS implements at kernel level in notebook §14.4.
    """
    return jsonify({"identities": list_identities()})


@data_bp.route("/api/data/tables/<schema>/<table>/rows", methods=["GET"])
def get_rows(schema: str, table: str):
    """Fetch up to `limit` rows from a specific table.

    Query params:
      - limit   (default 100, max 500)
      - offset  (default 0)
      - search  (optional substring; runs LOWER(LIKE) on every VARCHAR2 column)
      - as_user (identity id from /api/identities; controls row filter + masks)
    """
    # Outer try → guarantees JSON, never an HTML 500 page from Flask
    try:
        conn = _state.get("agent_conn")
        if not conn:
            return jsonify({"error": "not initialized"}), 503

        identity = get_identity(request.args.get("as_user"))

        # Synthetic DBFS schema → list files instead of running SQL
        if schema.upper() == "DBFS" and table.lower() == "scratchpad":
            return _dbfs_scratchpad_rows(conn, request.args.get("search", "").strip())

        qualified = _safe_table_name(schema, table)
        if not qualified:
            return jsonify({"error": f"unknown table {schema}.{table}"}), 404

        if is_table_forbidden(identity, schema, table):
            return jsonify({
                "error": (
                    f"identity {identity.id!r} is not authorized to read "
                    f"{schema.upper()}.{table.upper()} "
                    f"({identity.label}, clearance={identity.clearance})."
                ),
                "identity": identity.as_json(),
            }), 403

        limit = min(int(request.args.get("limit", "100")), 500)
        offset = max(int(request.args.get("offset", "0")), 0)
        search = (request.args.get("search") or "").strip()

        # Schema introspection.
        # NOTE: AGENT has SELECT ANY TABLE + SELECT_CATALOG_ROLE. With those,
        # ALL_TAB_COLUMNS does *not* return rows for objects AGENT only reaches
        # via system privilege — that was the source of the
        # "no columns visible — check grants" error users hit on SUPPLYCHAIN
        # tables. DBA_TAB_COLUMNS is exposed by SELECT_CATALOG_ROLE and lists
        # every column regardless of object-level grants.
        columns: list[dict] = []
        with conn.cursor() as cur:
            cur.execute(
                "SELECT column_name, data_type, data_length, nullable "
                "  FROM dba_tab_columns "
                " WHERE owner = :o AND table_name = :t "
                " ORDER BY column_id",
                o=schema.upper(), t=table.upper(),
            )
            for name, dtype, dlen, null in cur:
                columns.append({
                    "name": name,
                    "type": dtype,
                    "length": dlen,
                    "nullable": null == "Y",
                    "masked": column_is_masked(identity, schema, table, name),
                })

        if not columns:
            return jsonify({
                "error": (
                    "no columns visible in DBA_TAB_COLUMNS — check that AGENT "
                    "has SELECT_CATALOG_ROLE and that the table actually exists."
                ),
            }), 500

        # Drop columns we know we can't render — vectors mostly. The grid still
        # gets type metadata for the dropped columns so the user can see they
        # exist.
        rendered_cols = [c for c in columns if c["type"] not in SKIP_COLUMN_TYPES]
        col_names = [c["name"] for c in rendered_cols]
        if not col_names:
            return jsonify({"error": "all columns are skipped (vector-only table?)"}), 500
        col_list = ", ".join(col_names)

        # Compose WHERE: identity-driven row filter ∧ optional text search.
        where_clauses: list[str] = []
        binds: dict[str, Any] = {"limit": limit, "offset": offset}

        ident_clause, ident_binds = region_filter_clause(identity, schema, table)
        if ident_clause:
            where_clauses.append(ident_clause)
            binds.update(ident_binds)

        if search:
            text_cols = [c["name"] for c in rendered_cols
                         if c["type"] in ("VARCHAR2", "CHAR", "CLOB")]
            if text_cols:
                ors = []
                for i, name in enumerate(text_cols):
                    key = f"q{i}"
                    if name in ("BODY", "DESCRIPTION", "NOTES"):
                        ors.append(
                            f"LOWER(DBMS_LOB.SUBSTR({name}, 4000, 1)) LIKE :{key}"
                        )
                    else:
                        ors.append(f"LOWER({name}) LIKE :{key}")
                    binds[key] = f"%{search.lower()}%"
                where_clauses.append("(" + " OR ".join(ors) + ")")

        where_sql = (" WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

        # Row count
        count_sql = f"SELECT COUNT(*) FROM {qualified}{where_sql}"
        sql = (f"SELECT {col_list} FROM {qualified}{where_sql} "
               "ORDER BY 1 OFFSET :offset ROWS FETCH NEXT :limit ROWS ONLY")
        rows: list[list[Any]] = []
        with conn.cursor() as cur:
            # The COUNT query doesn't use OFFSET/LIMIT; pass everything else.
            count_binds = {k: v for k, v in binds.items()
                           if k != "limit" and k != "offset"}
            cur.execute(count_sql, count_binds)
            total = cur.fetchone()[0]

            cur.execute(sql, binds)
            mask_idx = {i: c for i, c in enumerate(rendered_cols) if c.get("masked")}
            for row in cur:
                rendered = [_render_value(v) for v in row]
                # Apply identity-driven column masks after fetch — the kernel
                # returns the values, we drop them before they leave the API.
                for j in mask_idx:
                    rendered[j] = "[REDACTED]"
                rows.append(rendered)

        return jsonify({
            "schema": schema.upper(),
            "table": table.upper(),
            "columns": rendered_cols,  # only the columns we actually returned
            "skipped_columns": [c for c in columns if c["type"] in SKIP_COLUMN_TYPES],
            "rows": rows,
            "row_count": total,
            "returned": len(rows),
            "limit": limit,
            "offset": offset,
            "search": search,
            "identity": identity.as_json(),
        })
    except oracledb.DatabaseError as e:
        traceback.print_exc()
        return jsonify({"error": f"OracleError: {e}"}), 500
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"{type(e).__name__}: {e}"}), 500


def _dbfs_scratchpad_rows(conn, search: str = ""):
    """Render the DBFS scratchpad as a 4-column virtual table for the grid.

    Every file's owning thread is extracted from its path
    (/scratch/threads/<thread_id>/<rel>) so you can see per-thread isolation
    at a glance. Files outside /scratch/threads/ show 'shared' as the owner.
    """
    from db.dbfs import DBFS
    scratch = DBFS(conn)
    paths = scratch.list("/")
    rows: list[list[Any]] = []
    needle = search.lower() if search else ""
    for p in paths or []:
        try:
            content = scratch.read(p)
        except Exception as e:
            content = f"[unreadable: {type(e).__name__}: {e}]"
        if needle and needle not in p.lower() and needle not in (content or "").lower():
            continue
        size_bytes = len(content) if isinstance(content, str) else 0
        # Extract the owning thread id from the path. We chose to organize
        # scratch files under /scratch/threads/<thread_id>/ in tools.py.
        thread_id = "shared"
        marker = "/scratch/threads/"
        if p.startswith(marker):
            rest = p[len(marker):]
            thread_id = rest.split("/", 1)[0] if "/" in rest else rest
        rows.append([thread_id, p, size_bytes, (content or "")[:1500]])

    columns = [
        {"name": "THREAD_ID", "type": "VARCHAR2", "length": 64,  "nullable": False},
        {"name": "PATH",      "type": "VARCHAR2", "length": 400, "nullable": False},
        {"name": "BYTES",     "type": "NUMBER",   "length": None, "nullable": False},
        {"name": "PREVIEW",   "type": "CLOB",     "length": None, "nullable": True},
    ]
    return jsonify({
        "schema": "DBFS",
        "table": "scratchpad",
        "columns": columns,
        "skipped_columns": [],
        "rows": rows,
        "row_count": len(rows),
        "returned": len(rows),
        "limit": 100,
        "offset": 0,
        "search": search,
    })


@data_bp.route("/api/data/scan/<schema>", methods=["POST"])
def scan_schema(schema: str):
    """Run the §5 schema scanner against `schema` and write facts to OAMP.

    Same path the agent's `scan_database` tool takes — exposed so the front-end
    can refresh institutional knowledge with one click whenever the underlying
    data has changed.
    """
    try:
        s = schema.upper()
        if s not in TABLE_ALLOWLIST:
            return jsonify({"error": f"unknown schema {schema!r}"}), 404

        conn = _state.get("agent_conn")
        mc = _state.get("memory_client")
        if not conn or not mc:
            return jsonify({"error": "not initialized"}), 503

        from retrieval.scanner import run_scan
        summary = run_scan(conn, mc, s)
        return jsonify({"ok": True, "schema": s, "summary": summary})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"{type(e).__name__}: {e}"}), 500


@data_bp.errorhandler(Exception)
def _handle_blueprint_errors(e):
    """Last-resort guard so the front-end always sees JSON, never HTML."""
    traceback.print_exc()
    return jsonify({"error": f"{type(e).__name__}: {e}"}), 500
