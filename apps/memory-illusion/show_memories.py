"""Peek straight into the database — the 'Memory updated' rows, via plain SQL.

Run AFTER demo2:  ./.venv/bin/python show_memories.py
Great on camera: proves agent memory is literally rows in Oracle.
"""

import oracledb
from config import ORACLE_DSN, ORACLE_PASSWORD, ORACLE_USER
from rich.console import Console
from rich.table import Table

console = Console()
conn = oracledb.connect(user=ORACLE_USER, password=ORACLE_PASSWORD, dsn=ORACLE_DSN)
cur = conn.cursor()

console.print("\n[bold]Tables the memory layer manages in this schema:[/]")
cur.execute("SELECT table_name FROM user_tables ORDER BY table_name")
tables = [r[0] for r in cur.fetchall()]
for t in tables:
    console.print(f"  [cyan]▸[/] {t}")

mem_table = next((t for t in tables if "MEMORY" in t and "STORE" not in t), None)
if mem_table:
    console.print(f"\n[bold]SELECT * FROM {mem_table} — your extracted memories:[/]\n")
    cur.execute(f"""
        SELECT record_id, memory_type, user_id, agent_id,
               DBMS_LOB.SUBSTR(content, 300, 1) AS content
        FROM {mem_table} ORDER BY created_at""")
    cols = [d[0] for d in cur.description]
    tab = Table(show_lines=True, header_style="bold green")
    for c in ["TYPE", "USER_ID", "CONTENT"]:
        tab.add_column(c, overflow="fold")
    for row in cur.fetchall():
        rec = dict(zip(cols, row, strict=False))
        tab.add_row(str(rec.get("MEMORY_TYPE")), str(rec.get("USER_ID")), str(rec.get("CONTENT")))
    console.print(tab)
else:
    console.print("[yellow]No memory table found yet — run demo2 first.[/]")

conn.close()
