"""Oracle database connection management using python-oracledb."""

import json
import logging
from collections.abc import Generator
from contextlib import contextmanager
from typing import Any

import oracledb

from fittrack.core.config import get_settings

logger = logging.getLogger(__name__)

# Global connection pool
_pool: oracledb.ConnectionPool | None = None


def _output_type_handler(cursor, metadata):
    """Output type handler to convert LOBs to strings."""
    if metadata.type_code is oracledb.DB_TYPE_CLOB:
        return cursor.var(oracledb.DB_TYPE_LONG, arraysize=cursor.arraysize)
    if metadata.type_code is oracledb.DB_TYPE_BLOB:
        return cursor.var(oracledb.DB_TYPE_LONG_RAW, arraysize=cursor.arraysize)
    if metadata.type_code is oracledb.DB_TYPE_JSON:
        return cursor.var(str, arraysize=cursor.arraysize)


def init_pool() -> oracledb.ConnectionPool:
    """Initialize the Oracle connection pool."""
    global _pool
    if _pool is not None:
        return _pool

    settings = get_settings()

    logger.info(f"Initializing Oracle connection pool to {settings.oracle_dsn}")

    _pool = oracledb.create_pool(
        user=settings.oracle_user,
        password=settings.oracle_password,
        dsn=settings.oracle_dsn,
        min=2,
        max=10,
        increment=1,
        getmode=oracledb.POOL_GETMODE_WAIT,
        wait_timeout=30,
    )

    logger.info("Oracle connection pool initialized")
    return _pool


def get_pool() -> oracledb.ConnectionPool:
    """Get the connection pool, initializing if needed."""
    global _pool
    if _pool is None:
        return init_pool()
    return _pool


def close_pool() -> None:
    """Close the connection pool."""
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None
        logger.info("Oracle connection pool closed")


@contextmanager
def get_connection() -> Generator[oracledb.Connection, None, None]:
    """Get a connection from the pool."""
    pool = get_pool()
    connection = pool.acquire()
    connection.outputtypehandler = _output_type_handler
    try:
        yield connection
    finally:
        pool.release(connection)


@contextmanager
def get_cursor() -> Generator[oracledb.Cursor, None, None]:
    """Get a cursor from a pooled connection."""
    with get_connection() as connection:
        cursor = connection.cursor()
        try:
            yield cursor
        finally:
            cursor.close()


def execute_query(
    sql: str,
    params: dict[str, Any] | list[Any] | None = None,
) -> list[dict[str, Any]]:
    """Execute a query and return results as list of dicts."""
    with get_cursor() as cursor:
        cursor.execute(sql, params or {})
        columns = [col[0].lower() for col in cursor.description or []]
        return [dict(zip(columns, row, strict=False)) for row in cursor.fetchall()]


def execute_query_one(
    sql: str,
    params: dict[str, Any] | list[Any] | None = None,
) -> dict[str, Any] | None:
    """Execute a query and return single result as dict."""
    with get_cursor() as cursor:
        cursor.execute(sql, params or {})
        row = cursor.fetchone()
        if row is None:
            return None
        columns = [col[0].lower() for col in cursor.description or []]
        return dict(zip(columns, row, strict=False))


def execute_dml(
    sql: str,
    params: dict[str, Any] | list[Any] | None = None,
    commit: bool = True,
) -> int:
    """Execute DML (INSERT/UPDATE/DELETE) and return rowcount."""
    with get_connection() as connection:
        cursor = connection.cursor()
        try:
            cursor.execute(sql, params or {})
            rowcount = cursor.rowcount
            if commit:
                connection.commit()
            return rowcount
        finally:
            cursor.close()


def execute_dml_returning(
    sql: str,
    params: dict[str, Any] | list[Any] | None = None,
    returning_vars: dict[str, Any] | None = None,
    commit: bool = True,
) -> dict[str, Any]:
    """Execute DML with RETURNING clause."""
    with get_connection() as connection:
        cursor = connection.cursor()
        try:
            # Bind output variables
            out_vars = {}
            if returning_vars:
                for name, var_type in returning_vars.items():
                    out_vars[name] = cursor.var(var_type)
                params = {**(params or {}), **out_vars}

            cursor.execute(sql, params)

            if commit:
                connection.commit()

            # Extract returned values
            result = {}
            for name, var in out_vars.items():
                value = var.getvalue()
                # Handle LOB types
                if hasattr(value, "read"):
                    value = value.read()
                result[name] = value

            return result
        finally:
            cursor.close()


def execute_json_query(
    duality_view: str,
    where_clause: str | None = None,
    params: dict[str, Any] | None = None,
    order_by: str | None = None,
    limit: int | None = None,
    offset: int | None = None,
) -> list[dict[str, Any]]:
    """Query a JSON Duality View and return parsed JSON documents."""
    sql = f"SELECT data FROM {duality_view}"

    if where_clause:
        sql += f" WHERE {where_clause}"

    if order_by:
        sql += f" ORDER BY {order_by}"

    if offset is not None:
        sql += f" OFFSET {offset} ROWS"
    if limit is not None:
        sql += f" FETCH NEXT {limit} ROWS ONLY"

    results = execute_query(sql, params or {})
    documents = []
    for row in results:
        data = row.get("data")
        if data:
            if isinstance(data, str):
                documents.append(json.loads(data))
            elif isinstance(data, bytes):
                documents.append(json.loads(data.decode("utf-8")))
            elif hasattr(data, "read"):
                content = data.read()
                if isinstance(content, bytes):
                    content = content.decode("utf-8")
                documents.append(json.loads(content))
            elif isinstance(data, dict):
                documents.append(data)
            else:
                documents.append(data)
    return documents


def insert_json_document(
    duality_view: str,
    document: dict[str, Any],
    commit: bool = True,
) -> dict[str, Any]:
    """Insert a JSON document into a Duality View."""
    json_data = json.dumps(document)
    sql = f"INSERT INTO {duality_view} (data) VALUES (:data)"

    with get_connection() as connection:
        cursor = connection.cursor()
        try:
            cursor.execute(sql, {"data": json_data})
            if commit:
                connection.commit()
            return document
        finally:
            cursor.close()


def update_json_document(
    duality_view: str,
    id_field: str,
    id_value: str,
    document: dict[str, Any],
    commit: bool = True,
) -> bool:
    """Update a JSON document in a Duality View."""
    json_data = json.dumps(document)
    sql = f"""
        UPDATE {duality_view}
        SET data = :data
        WHERE JSON_VALUE(data, '$.{id_field}') = :id_value
    """

    rowcount = execute_dml(sql, {"data": json_data, "id_value": id_value}, commit=commit)
    return rowcount > 0


def delete_json_document(
    duality_view: str,
    id_field: str,
    id_value: str,
    commit: bool = True,
) -> bool:
    """Delete a JSON document from a Duality View."""
    sql = f"""
        DELETE FROM {duality_view}
        WHERE JSON_VALUE(data, '$.{id_field}') = :id_value
    """

    rowcount = execute_dml(sql, {"id_value": id_value}, commit=commit)
    return rowcount > 0


def count_json_documents(
    duality_view: str,
    where_clause: str | None = None,
    params: dict[str, Any] | None = None,
) -> int:
    """Count documents in a JSON Duality View."""
    sql = f"SELECT COUNT(*) as cnt FROM {duality_view}"

    if where_clause:
        sql += f" WHERE {where_clause}"

    result = execute_query_one(sql, params or {})
    return result["cnt"] if result else 0


def health_check() -> bool:
    """Check database connectivity."""
    try:
        result = execute_query_one("SELECT 1 as ok FROM DUAL")
        return result is not None and result.get("ok") == 1
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False
