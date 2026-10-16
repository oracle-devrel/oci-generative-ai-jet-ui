from workshop.memory import Fact, TABLES_SQL

# TODO 3: write the two marked spots in the loop (about 3 lines; the rest is written for you).
#   Spot 1: copy the pattern of the "Documented purpose" lines, but only when num_rows is not None,
#           append the sentence "Approximate row count: {num_rows:,}." to `parts` (the :, adds thousands commas).
#   Spot 2: append one Fact to `facts` with Fact(kind, subject, body, metadata):
#             kind     = "table"
#             subject  = "{owner}.{table}" as one string, e.g. "FINANCE.TRANSACTIONS"
#             body     = the `body` string built below
#             metadata = a dict with keys "owner" (owner), "table" (table), "num_rows" (num_rows)
#                        and "has_comment" (True if the table has a comment, else False: use bool(comment))
#   Guide: docs/part-2-oamp-memory.md#todo-3-_scan_tables
def _scan_tables(conn, owner: str) -> list[Fact]:
    facts = []
    with conn.cursor() as cur:
        cur.execute(TABLES_SQL, owner=owner.upper())
        for table, comment, num_rows, last_analyzed in cur:
            parts = [f"Table {owner}.{table}."]
            if comment:
                parts.append(f"Documented purpose: {comment}")   # worked example
            # TODO 3a: if num_rows is not None, parts.append(the row-count sentence)
            raise NotImplementedError("TODO 3a: add the row-count sentence to parts when num_rows is not None")
            if last_analyzed:
                parts.append(f"Statistics last gathered at {last_analyzed}.")
            body = " ".join(parts)
            # TODO 3b: facts.append(Fact(kind, subject, body, metadata)) as described above
            raise NotImplementedError("TODO 3b: facts.append(Fact(...))")
    return facts
