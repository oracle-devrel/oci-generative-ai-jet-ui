"""QueryLogger: intercepts every DB query and emits it via WebSocket for the right pane."""

import time
import uuid

import eventlet


class QueryLogger:
    """Intercepts database queries and emits them via WebSocket for the UI."""

    QUERY_TYPE_PATTERNS = {
        # Oracle
        "VECTOR_DISTANCE": "vector",
        "CONTAINS(": "text",
        "GRAPH_TABLE(": "graph",
        "JSON_VALUE(": "json",
        "JSON_QUERY(": "json",
        "SDO_WITHIN_DISTANCE": "spatial",
        "SDO_NN(": "spatial",
        "SDO_GEOM.SDO_DISTANCE": "spatial",
        # PostgreSQL / PostGIS
        "ST_DISTANCESPHERE": "spatial",
        "ST_DWITHIN": "spatial",
        "TO_TSVECTOR": "text",
        "PLAINTO_TSQUERY": "text",
        "->>'": "json",
        "->'": "json",
    }

    def __init__(self, socketio=None):
        self.socketio = socketio
        self.queries = []  # in-memory log for current request

    def classify_query(self, sql):
        """Classify query type based on SQL content."""
        sql_upper = sql.upper()

        has_vector = "VECTOR_DISTANCE" in sql_upper
        has_text = "CONTAINS(" in sql_upper
        has_graph = "GRAPH_TABLE(" in sql_upper
        has_json = "JSON_VALUE(" in sql_upper or "JSON_QUERY(" in sql_upper
        has_spatial = "SDO_WITHIN_DISTANCE" in sql_upper or "SDO_NN(" in sql_upper

        # Count paradigms present in the query
        paradigm_count = sum([has_vector, has_text, has_graph, has_json, has_spatial])

        # Convergent: 2+ paradigms including graph, vector, or spatial
        if paradigm_count >= 2 and (has_graph or has_spatial or (has_vector and has_graph)):
            return "convergent"

        # Hybrid: vector + text (classic hybrid search)
        if has_vector and has_text:
            return "hybrid"

        for pattern, query_type in self.QUERY_TYPE_PATTERNS.items():
            if pattern in sql_upper:
                return query_type

        return "relational"

    def execute_and_log(self, cursor, sql, params=None, description=""):
        """Execute a query, log it, and emit via WebSocket.

        Logs and emits both successful and failed queries so the Database pane
        always shows activity.
        """
        query_id = str(uuid.uuid4())[:8]
        query_type = self.classify_query(sql)
        start_time = time.time()

        try:
            if params:
                cursor.execute(sql, params)
            else:
                cursor.execute(sql)

            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            elapsed_ms = round((time.time() - start_time) * 1000, 1)
            error_msg = None
        except Exception as e:
            rows = []
            columns = []
            elapsed_ms = round((time.time() - start_time) * 1000, 1)
            error_msg = str(e)

        query_record = {
            "id": query_id,
            "type": query_type,
            "sql": sql.strip(),
            "params": str(params) if params else None,
            "elapsed_ms": elapsed_ms,
            "result_count": len(rows),
            "top_result_preview": self._preview(rows, columns),
            "timestamp": time.time(),
            "description": description,
        }
        if error_msg:
            query_record["error"] = error_msg

        self.queries.append(query_record)

        if self.socketio:
            self.socketio.emit("query_executed", query_record)
            eventlet.sleep(0)  # Yield to flush WebSocket message immediately

        # Re-raise so the caller still sees the failure
        if error_msg:
            raise Exception(error_msg)

        return rows, columns

    def _preview(self, rows, columns, max_rows=2):
        """Generate a preview of results for the UI card."""
        if not rows or not columns:
            return None
        preview = []
        for row in rows[:max_rows]:
            preview.append(
                dict(
                    zip(columns, [str(v)[:100] if v is not None else "" for v in row], strict=False)
                )
            )
        return preview

    def log_external_query(
        self, query_text, query_type, description="", elapsed_ms=0, result_count=0, params=None
    ):
        """Log a non-SQL query (Neo4j Cypher, Qdrant vector search, etc.)."""
        query_id = str(uuid.uuid4())[:8]
        query_record = {
            "id": query_id,
            "type": query_type,
            "sql": query_text.strip(),
            "params": str(params) if params else None,
            "elapsed_ms": elapsed_ms,
            "result_count": result_count,
            "top_result_preview": None,
            "timestamp": time.time(),
            "description": description,
        }
        self.queries.append(query_record)
        if self.socketio:
            self.socketio.emit("query_executed", query_record)
            eventlet.sleep(0)

    def clear(self):
        """Clear the in-memory query log for the current request."""
        self.queries.clear()

    def get_summary(self):
        """Get summary stats for the sticky footer."""
        if not self.queries:
            return {"query_count": 0, "type_count": 0, "total_ms": 0}
        types = {q["type"] for q in self.queries}
        total_ms = sum(q["elapsed_ms"] for q in self.queries)
        return {
            "query_count": len(self.queries),
            "type_count": len(types),
            "total_ms": round(total_ms, 1),
        }
