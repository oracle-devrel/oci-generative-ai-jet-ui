from memory.db import connect_sync
from memory.ddl import create_all, drop_all, TABLES


def test_ddl_create_and_drop():
    conn = connect_sync()
    try:
        drop_all(conn)
        create_all(conn)
        cur = conn.cursor()
        # Compare lowercase table names to be portable.
        cur.execute(
            "SELECT LOWER(table_name) FROM user_tables WHERE LOWER(table_name) IN "
            "(" + ",".join(f"'{t}'" for t in TABLES) + ")"
        )
        rows = sorted(r[0] for r in cur)
        assert rows == sorted(TABLES)
    finally:
        conn.close()
