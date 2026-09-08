"""Generic MongoDB-to-Oracle JSON landing path.

This path is intentionally conservative: it preserves arbitrary MongoDB
documents in an Oracle JSON column and creates a first-pass scalar projection
for top-level scalar fields. Rich product-review migrations still use the
hand-authored Duality path in duality.py.
"""

from __future__ import annotations

import json
import re
from datetime import date, datetime
from typing import Any

from data_migration_harness.environment import oracle_pool

RAW_TABLE = "mongo_raw_docs"
PROJECTION_TABLE = "mongo_scalar_projection"
_RESERVED = {
    "select",
    "from",
    "where",
    "table",
    "view",
    "group",
    "order",
    "by",
    "date",
    "number",
    "json",
    "create",
    "drop",
    "insert",
    "update",
    "delete",
    "index",
}


def _json_default(value):
    if isinstance(value, datetime | date):
        return value.isoformat()
    return str(value)


def _identifier(name: str, used: set[str]) -> str:
    out = re.sub(r"[^a-zA-Z0-9_]", "_", name).lower().strip("_") or "field"
    if out[0].isdigit():
        out = "c_" + out
    if out in _RESERVED:
        out = "field_" + out
    out = out[:26]
    base = out
    i = 2
    while out in used:
        suffix = f"_{i}"
        out = base[: 30 - len(suffix)] + suffix
        i += 1
    used.add(out)
    return out


def _scalar_type(values: list[Any]) -> str | None:
    non_null = [v for v in values if v is not None]
    if not non_null:
        return "VARCHAR2(4000)"
    if all(isinstance(v, bool) for v in non_null):
        return "NUMBER(1)"
    if all(isinstance(v, int | float) and not isinstance(v, bool) for v in non_null):
        return "NUMBER"
    if all(isinstance(v, str | datetime | date) for v in non_null):
        return "VARCHAR2(4000)"
    if any(isinstance(v, dict | list) for v in non_null):
        return None
    return "VARCHAR2(4000)"


def infer_projection(docs: list[dict]) -> list[dict]:
    values: dict[str, list[Any]] = {}
    for doc in docs:
        for k, v in doc.items():
            if k == "_id" or isinstance(v, dict | list):
                continue
            values.setdefault(k, []).append(v)
    used = {"id", "mongo_id", "migrated_at"}
    cols = []
    for source_name, vals in values.items():
        typ = _scalar_type(vals)
        if typ:
            cols.append(
                {"source": source_name, "name": _identifier(source_name, used), "type": typ}
            )
    return cols[:40]


def drop_generic_tables() -> None:
    pool = oracle_pool()
    with pool.acquire() as conn:
        cur = conn.cursor()
        for stmt in (f"DROP TABLE {PROJECTION_TABLE}", f"DROP TABLE {RAW_TABLE}"):
            try:
                cur.execute(stmt)
            except Exception:
                pass
        conn.commit()


def create_raw_table() -> None:
    pool = oracle_pool()
    with pool.acquire() as conn:
        cur = conn.cursor()
        try:
            cur.execute(f"DROP TABLE {RAW_TABLE}")
        except Exception:
            pass
        cur.execute(
            f"""
            CREATE TABLE {RAW_TABLE} (
                id NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                mongo_id VARCHAR2(64) UNIQUE,
                doc JSON NOT NULL,
                migrated_at TIMESTAMP DEFAULT SYSTIMESTAMP
            )
        """
        )
        conn.commit()


def land_documents(docs: list[dict]) -> int:
    pool = oracle_pool()
    with pool.acquire() as conn:
        cur = conn.cursor()
        rows = []
        for d in docs:
            mid = str(d.get("_id"))
            payload = {k: v for k, v in d.items() if k != "_id"}
            payload["_mongo_id"] = mid
            rows.append((mid, json.dumps(payload, default=_json_default)))
        if rows:
            cur.executemany(f"INSERT INTO {RAW_TABLE} (mongo_id, doc) VALUES (:1, :2)", rows)
        conn.commit()
    return len(rows)


def create_scalar_projection(docs: list[dict]) -> list[dict]:
    cols = infer_projection(docs)
    if not cols:
        return []
    pool = oracle_pool()
    with pool.acquire() as conn:
        cur = conn.cursor()
        try:
            cur.execute(f"DROP TABLE {PROJECTION_TABLE}")
        except Exception:
            pass
        col_sql = ",\n".join(f"                {c['name']} {c['type']}" for c in cols)
        cur.execute(
            f"""
            CREATE TABLE {PROJECTION_TABLE} (
                id NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                mongo_id VARCHAR2(64) UNIQUE,
{col_sql}
            )
        """
        )
        insert_cols = ["mongo_id"] + [c["name"] for c in cols]
        binds = [f":{i + 1}" for i in range(len(insert_cols))]
        rows = []
        for d in docs:
            row = [str(d.get("_id"))]
            for c in cols:
                v = d.get(c["source"])
                if isinstance(v, bool):
                    v = 1 if v else 0
                elif isinstance(v, datetime | date):
                    v = v.isoformat()
                row.append(v)
            rows.append(tuple(row))
        if rows:
            cur.executemany(
                f"INSERT INTO {PROJECTION_TABLE} ({', '.join(insert_cols)}) VALUES ({', '.join(binds)})",
                rows,
            )
        conn.commit()
    return cols


def raw_ddl() -> str:
    return f"""CREATE TABLE {RAW_TABLE} (
    id NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    mongo_id VARCHAR2(64) UNIQUE,
    doc JSON NOT NULL,
    migrated_at TIMESTAMP DEFAULT SYSTIMESTAMP
)"""


def projection_ddl(cols: list[dict]) -> str:
    if not cols:
        return "-- No top-level scalar fields detected for projection."
    col_sql = ",\n".join(f"    {c['name']} {c['type']} -- from {c['source']}" for c in cols)
    return f"""CREATE TABLE {PROJECTION_TABLE} (
    id NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    mongo_id VARCHAR2(64) UNIQUE,
{col_sql}
)"""


def inspect() -> dict:
    pool = oracle_pool()
    with pool.acquire() as conn:
        cur = conn.cursor()
        cur.execute(f"SELECT COUNT(*) FROM {RAW_TABLE}")
        raw_count = cur.fetchone()[0]
        cur.execute(
            f"SELECT mongo_id, JSON_SERIALIZE(doc RETURNING CLOB PRETTY) FROM {RAW_TABLE} FETCH FIRST 1 ROWS ONLY"
        )
        sample_row = cur.fetchone()
        sample = None
        if sample_row:
            sample = {
                "mongo_id": sample_row[0],
                "doc": json.loads(
                    sample_row[1].read() if hasattr(sample_row[1], "read") else sample_row[1]
                ),
            }
        projection = []
        try:
            cur.execute(f"SELECT * FROM {PROJECTION_TABLE} FETCH FIRST 5 ROWS ONLY")
            cols = [c[0].lower() for c in cur.description]
            projection = [dict(zip(cols, row, strict=False)) for row in cur.fetchall()]
        except Exception:
            pass
        return {"raw_count": raw_count, "sample": sample, "projection": projection}
