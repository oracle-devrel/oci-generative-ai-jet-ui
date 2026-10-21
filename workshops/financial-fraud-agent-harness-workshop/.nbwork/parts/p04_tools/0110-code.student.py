import json
import re

_READ_ONLY = re.compile(r"^\s*(select|with)\b", re.IGNORECASE)

@register
def tool_run_sql(sql: str, max_rows: int = 50) -> str:
    """Execute a READ-ONLY SQL statement (SELECT/WITH only) against the Oracle AI Database and return up to `max_rows` rows as JSON."""
    if not _READ_ONLY.match(sql.strip()):   # anything that is not SELECT/WITH is refused
        return json.dumps({"error": "only SELECT / WITH statements are allowed in run_sql"})
    try:
        with agent_conn.cursor() as cur:
            # TODO 6 (two lines): run the statement, then return its rows as JSON. Write:
            #     cur.execute(<the statement>)
            #     return wt.rows_json(cur, <the row limit>)
            #   <the statement>  sql        (the SQL text the agent sent)
            #   <the row limit>  max_rows   (rows_json returns {"columns": [...], "rows": [[...]], "row_count": N})
            raise NotImplementedError("TODO 6: cur.execute(...) then return wt.rows_json(...)")
    except Exception as e:   # any database error goes back to the agent as JSON
        return json.dumps({"error": str(e)})
