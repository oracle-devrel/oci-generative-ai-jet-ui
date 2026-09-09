#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../../../.."

uv run python - <<'PY'
import os, oracledb
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path.cwd() / ".env")

admin_pw = os.environ["ORACLE_ADMIN_PASSWORD"]
user = os.environ["ORACLE_USER"]
pw = os.environ["ORACLE_PASSWORD"]
dsn = os.environ["ORACLE_DSN"]

with oracledb.connect(user="system", password=admin_pw, dsn=dsn) as conn:
    cur = conn.cursor()
    cur.execute(
        "BEGIN EXECUTE IMMEDIATE 'DROP USER " + user + " CASCADE'; "
        "EXCEPTION WHEN OTHERS THEN NULL; END;"
    )
    cur.execute(f'CREATE USER {user} IDENTIFIED BY "{pw}"')
    cur.execute(f"GRANT CONNECT, RESOURCE, UNLIMITED TABLESPACE TO {user}")
    cur.execute(f"GRANT CREATE VIEW, CREATE SESSION TO {user}")
    cur.execute(f"GRANT CREATE MINING MODEL TO {user}")
    conn.commit()
print(f"User {user} ready (with CREATE MINING MODEL).")
PY
