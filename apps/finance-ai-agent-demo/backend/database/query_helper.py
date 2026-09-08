"""Reusable query execution helper with optional query logging."""


def execute_query(conn, sql, params, query_logger=None, description=""):
    """Execute a SQL query with optional logging, returning (rows, columns).

    Encapsulates the repeated pattern of query_logger-aware execution
    used across tools and retrieval modules.
    """
    with conn.cursor() as cur:
        if query_logger:
            return query_logger.execute_and_log(cur, sql, params, description=description)
        cur.execute(sql, params)
        rows = cur.fetchall()
        columns = [d[0] for d in cur.description] if cur.description else []
        return rows, columns
