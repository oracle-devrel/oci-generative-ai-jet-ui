"""One-time database bootstrap: app users, grants, and the in-database embedding model.

Run once against a fresh Oracle AI Database Free container (see docker-compose.yml):

    uv run python scripts/bootstrap_db.py

It connects as SYS (password from ORACLE_SYS_PASSWORD / ORACLE_PWD) and, for the
dev schema and the test schema:

  1. creates the user with a USERS-tablespace quota,
  2. grants exactly what team-brain needs (tables, Oracle Text, the vector
     packages, DBMS_RLS for the row policy, DBMS_SESSION for the trusted
     application context, CREATE CONTEXT),
  3. loads Oracle's augmented all-MiniLM-L12-v2 ONNX model INTO the database so
     `VECTOR_EMBEDDING(...)` works as a SQL function (no embedding service, no
     Python model download).

Everything is idempotent: re-running skips what already exists.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import oracledb
from dotenv import load_dotenv
oracledb.defaults.program = "devrel-developerhub-team-brain"

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

DSN = os.getenv("ORACLE_DSN", "localhost:1521/FREEPDB1")
CONTAINER = os.getenv("ORACLE_CONTAINER", "team-brain-oracle")


def _sys_password() -> str:
    """SYS password: env var, else read ORACLE_PWD off the running container."""
    explicit = os.getenv("ORACLE_SYS_PASSWORD") or os.getenv("ORACLE_PWD")
    if explicit:
        return explicit
    import json
    import subprocess

    try:
        out = subprocess.run(
            ["docker", "inspect", CONTAINER], capture_output=True, text=True, check=True
        ).stdout
    except (OSError, subprocess.CalledProcessError):
        return ""
    env = dict(e.split("=", 1) for e in json.loads(out)[0]["Config"].get("Env", []) if "=" in e)
    # Oracle's image uses ORACLE_PWD; gvenzl/oracle-free uses ORACLE_PASSWORD.
    return env.get("ORACLE_PWD") or env.get("ORACLE_PASSWORD") or ""


SYS_PASSWORD = _sys_password()
APP_USER = os.getenv("ORACLE_USER", "TEAMBRAIN").upper()
APP_PASSWORD = os.getenv("ORACLE_PASSWORD", "TeamBrain123")
TEST_USER = os.getenv("ORACLE_USER_TEST", f"{APP_USER}_TEST").upper()
TEST_PASSWORD = os.getenv("ORACLE_PASSWORD_TEST", APP_PASSWORD)
ONNX_FILE = os.getenv("ONNX_FILENAME", "all_MiniLM_L12_v2.onnx")
MODEL_NAME = os.getenv("EMBEDDING_MODEL", "ALL_MINILM_L12_V2")

GRANTS = [
    "CONNECT, RESOURCE, CREATE SESSION, CREATE TABLE, CREATE VIEW, CREATE PROCEDURE, "
    "CREATE SEQUENCE, CREATE ANY CONTEXT, DROP ANY CONTEXT",
    "CREATE MINING MODEL",
    "DB_DEVELOPER_ROLE",
    "CTXAPP",
]
OBJECT_GRANTS = [
    "EXECUTE ON SYS.DBMS_VECTOR",
    "EXECUTE ON CTXSYS.DBMS_VECTOR_CHAIN",
    "EXECUTE ON SYS.DBMS_RLS",
    "EXECUTE ON SYS.DBMS_SESSION",
    "EXECUTE ON CTXSYS.CTX_DDL",
]


def _exists(cur: oracledb.Cursor, sql: str, *binds: object) -> bool:
    cur.execute(sql, binds)
    return cur.fetchone() is not None


def ensure_user(cur: oracledb.Cursor, user: str, password: str) -> None:
    if _exists(cur, "SELECT 1 FROM dba_users WHERE username = :1", user):
        print(f"  user {user}: exists")
    else:
        cur.execute(
            f'CREATE USER {user} IDENTIFIED BY "{password.replace(chr(34), chr(34) * 2)}" '
            "DEFAULT TABLESPACE USERS QUOTA UNLIMITED ON USERS"
        )
        print(f"  user {user}: created")
    for g in GRANTS:
        cur.execute(f"GRANT {g} TO {user}")
    for g in OBJECT_GRANTS:
        cur.execute(f"GRANT {g} TO {user}")
    print(f"  user {user}: grants applied")


ONNX_URL = os.getenv(
    "ONNX_URL",
    "https://adwc4pm.objectstorage.us-ashburn-1.oci.customer-oci.com"
    "/p/TtH6hL2y25EypZ0-rrczRZ1aXp7v1ONbRBfCiT-BDBN8WLKQ3lgyW6RxCfIFLdA6"
    "/n/adwc4pm/b/OML-ai-models/o/all_MiniLM_L12_v2_augmented.zip",
)
LOCAL_ONNX_DIR = Path(__file__).resolve().parent.parent / "oracle" / "onnx"
MODEL_METADATA = '{"function":"embedding","embeddingOutput":"embedding","input":{"input":["DATA"]}}'


def local_onnx_file() -> Path:
    """The .onnx file on this machine; downloaded + unzipped on first use (~117 MB)."""
    target = LOCAL_ONNX_DIR / ONNX_FILE
    if target.exists():
        return target
    import urllib.request
    import zipfile

    LOCAL_ONNX_DIR.mkdir(parents=True, exist_ok=True)
    archive = LOCAL_ONNX_DIR / "all_MiniLM_L12_v2_augmented.zip"
    if not archive.exists():
        print(f"  downloading {ONNX_URL} ...")
        urllib.request.urlretrieve(ONNX_URL, archive)
    with zipfile.ZipFile(archive) as zf:
        names = [n for n in zf.namelist() if n.endswith(".onnx")]
        if not names:
            raise RuntimeError(f"no .onnx file inside {archive}")
        zf.extract(names[0], LOCAL_ONNX_DIR)
        extracted = LOCAL_ONNX_DIR / names[0]
        if extracted != target:
            extracted.replace(target)
    return target


def ensure_model(user: str, password: str) -> None:
    conn = oracledb.connect(user=user, password=password, dsn=DSN)
    cur = conn.cursor()
    if _exists(cur, "SELECT 1 FROM user_mining_models WHERE model_name = :1", MODEL_NAME):
        print(f"  model {MODEL_NAME} in {user}: exists")
    else:
        # The model bytes travel over the database connection as a BLOB, so the
        # container needs no mounted directory and no file copy.
        model_bytes = local_onnx_file().read_bytes()
        cur.execute(
            """
            BEGIN
              DBMS_VECTOR.LOAD_ONNX_MODEL(
                model_name => :model_name,
                model_data => :model_data,
                metadata   => JSON(:meta));
            END;
            """,
            model_name=MODEL_NAME,
            model_data=model_bytes,
            meta=MODEL_METADATA,
        )
        conn.commit()
        print(
            f"  model {MODEL_NAME} in {user}: loaded ({len(model_bytes) // 1_000_000} MB via BLOB)"
        )
    cur.execute(
        f"SELECT vector_dims(VECTOR_EMBEDDING({MODEL_NAME} USING 'smoke test' AS DATA)) FROM dual"
    )
    dims = cur.fetchone()[0]
    print(f"  VECTOR_EMBEDDING({MODEL_NAME}) in {user}: {dims} dims")
    conn.close()


def main() -> int:
    if not SYS_PASSWORD:
        print("error: set ORACLE_SYS_PASSWORD (or ORACLE_PWD) to the container's SYS password")
        return 1
    sysconn = oracledb.connect(
        user="SYS", password=SYS_PASSWORD, dsn=DSN, mode=oracledb.AUTH_MODE_SYSDBA
    )
    cur = sysconn.cursor()
    cur.execute("SELECT banner_full FROM v$version")
    print(cur.fetchone()[0])

    cur.execute("SELECT value FROM v$parameter WHERE name = 'vector_memory_size'")
    vms = int(cur.fetchone()[0])
    if vms == 0:
        print(
            "  WARNING: vector_memory_size is 0. Exact vector search still works; "
            "vector INDEXES need a pool. Set with: ALTER SYSTEM SET vector_memory_size=512M "
            "SCOPE=SPFILE; then restart the container."
        )
    else:
        print(f"  vector_memory_size: {vms // (1024 * 1024)}M")

    for user, pwd in ((APP_USER, APP_PASSWORD), (TEST_USER, TEST_PASSWORD)):
        ensure_user(cur, user, pwd)
    sysconn.commit()
    sysconn.close()

    for user, pwd in ((APP_USER, APP_PASSWORD), (TEST_USER, TEST_PASSWORD)):
        ensure_model(user, pwd)
    print("bootstrap complete")
    return 0


if __name__ == "__main__":
    sys.exit(main())
