from workshop.memory import Fact, TABLES_SQL

# TODO 3: implement _scan_tables(conn, owner) -> list[Fact]
def _scan_tables(conn, owner: str) -> list[Fact]:
    facts = []
    with conn.cursor() as cur:
        cur.execute(TABLES_SQL, owner=owner.upper())
        for table, comment, num_rows, last_analyzed in cur:
            parts = [f"Table {owner}.{table}."]
            if comment:
                parts.append(f"Documented purpose: {comment}")
            if num_rows is not None:
                parts.append(f"Approximate row count: {num_rows:,}.")
            if last_analyzed:
                parts.append(f"Statistics last gathered at {last_analyzed}.")
            body = " ".join(parts)
            facts.append(Fact("table", f"{owner}.{table}", body,
                              {"owner": owner, "table": table, "num_rows": num_rows, "has_comment": bool(comment)}))
    return facts
