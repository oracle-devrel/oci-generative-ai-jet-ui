#!/usr/bin/env python3
"""Download the ALL_MINILM_L12_V2 ONNX model and load it into Oracle.

Runs once during Codespace post-create after `bootstrap.py`. Idempotent.

The Oracle database runs inside a separate Docker container (`oracle-free`)
that does NOT share the Codespace VM's filesystem. So the steps are:

  1. Download + unzip the .onnx file on the Codespace VM (under /tmp).
  2. `docker cp` it INTO the oracle-free container at /opt/oracle/onnx_models/.
  3. Create an Oracle DIRECTORY pointing at that in-container path.
  4. Call DBMS_VECTOR.LOAD_ONNX_MODEL (via langchain_oracledb's helper) to
     register it as ALL_MINILM_L12_V2.

After this step the AGENT schema has a mining model named ALL_MINILM_L12_V2
that the workshop's notebook uses through `OracleEmbeddings`:

    embeddings = OracleEmbeddings(
        conn=oracle_client,
        params={"provider": "database", "model": "ALL_MINILM_L12_V2"},
    )

The model produces 384-dim float vectors.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

import oracledb
from langchain_oracledb import OracleEmbeddings

# Public, pre-converted ONNX model from Oracle's OML samples bucket.
# Same URL used by enterprise_data_agent_harness_workshop_lightweight.
ONNX_URL = os.environ.get(
    "ONNX_URL",
    "https://adwc4pm.objectstorage.us-ashburn-1.oci.customer-oci.com"
    "/p/TtH6hL2y25EypZ0-rrczRZ1aXp7v1ONbRBfCiT-BDBN8WLKQ3lgyW6RxCfIFLdA6"
    "/n/adwc4pm/b/OML-ai-models/o/all_MiniLM_L12_v2_augmented.zip",
)
MODEL_NAME = os.environ.get("ONNX_EMBED_MODEL", "ALL_MINILM_L12_V2")
ONNX_FILENAME = os.environ.get("ONNX_FILENAME", "all_MiniLM_L12_v2.onnx")

ORACLE_CONTAINER = os.environ.get("ORACLE_CONTAINER", "oracle-free")
CONTAINER_MODEL_DIR = os.environ.get("ONNX_CONTAINER_DIR", "/opt/oracle/onnx_models")
ORACLE_DIR_NAME = os.environ.get("ONNX_ORACLE_DIRECTORY", "ONNX_DUMP")

AGENT_USER = os.environ.get("AGENT_USER", "AGENT")
AGENT_PASSWORD = os.environ.get("AGENT_PASSWORD", "AgentPwd_2025")
DSN = os.environ.get("ORACLE_DSN", "localhost:1521/FREEPDB1")


def _container_cli() -> str:
    """Return 'docker' if available, else 'podman'. Codespaces always has docker."""
    return "docker" if shutil.which("docker") else "podman"


def _exists_in_container(cli: str, path: str) -> bool:
    return (
        subprocess.run(
            [cli, "exec", ORACLE_CONTAINER, "test", "-f", path],
            capture_output=True,
        ).returncode
        == 0
    )


def _model_already_loaded(conn) -> bool:
    cur = conn.cursor()
    cur.execute(
        "SELECT COUNT(*) FROM user_mining_models WHERE model_name = :n",
        n=MODEL_NAME,
    )
    (n,) = cur.fetchone()
    return n > 0


def _stage_in_container() -> str:
    """Download, unzip on the host, copy into the Oracle container.

    Returns the in-container path of the .onnx file.
    """
    cli = _container_cli()
    if not shutil.which(cli):
        raise SystemExit(
            f"Cannot find {cli!r} on PATH. The Oracle DB runs in a separate\n"
            f"container; we need '{cli}' to stage the ONNX file into it."
        )

    target = f"{CONTAINER_MODEL_DIR}/{ONNX_FILENAME}"

    # If the container already has the file, skip the whole pipeline.
    subprocess.run(
        [cli, "exec", ORACLE_CONTAINER, "mkdir", "-p", CONTAINER_MODEL_DIR],
        check=True,
    )
    if _exists_in_container(cli, target):
        print(f"[onnx_setup] {target} already present in {ORACLE_CONTAINER} — reusing.")
        return target

    print(f"[onnx_setup] downloading {ONNX_URL} (~117 MB) …")
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        zip_path = tmp / "model.zip"
        try:
            urllib.request.urlretrieve(ONNX_URL, zip_path)
        except urllib.error.URLError as e:
            raise SystemExit(
                f"[onnx_setup] download failed: {e}. The pre-signed URL may have "
                "rotated. See: https://docs.oracle.com/en/database/oracle/oracle-database/26/"
                "vecse/import-onnx-models-oracle-database-end-end-example.html"
            ) from e

        print(f"[onnx_setup] extracting {ONNX_FILENAME} from archive …")
        with zipfile.ZipFile(zip_path) as zf:
            candidates = [n for n in zf.namelist() if n.endswith(".onnx")]
            if not candidates:
                raise RuntimeError(f"no .onnx file in archive {zip_path}")
            zf.extract(candidates[0], tmp)
            onnx_host_path = tmp / candidates[0]

        print(f"[onnx_setup] copying {onnx_host_path.name} → {ORACLE_CONTAINER}:{target}")
        subprocess.run(
            [cli, "cp", str(onnx_host_path), f"{ORACLE_CONTAINER}:{target}"],
            check=True,
        )
        # Ensure the oracle user inside the container can read it.
        subprocess.run(
            [cli, "exec", "--user", "0", ORACLE_CONTAINER, "chmod", "644", target],
            check=False,
            capture_output=True,
        )

    print(f"[onnx_setup] staged at {ORACLE_CONTAINER}:{target}")
    return target


def main() -> int:
    print("=" * 60)
    print("Supply-chain demand-planning workshop — ONNX model load")
    print("=" * 60)

    conn = oracledb.connect(user=AGENT_USER, password=AGENT_PASSWORD, dsn=DSN)

    if _model_already_loaded(conn):
        print(f"[onnx_setup] model {MODEL_NAME!r} already loaded — skipping.")
        return 0

    _stage_in_container()

    # Point Oracle at the in-container directory. AGENT has CREATE ANY DIRECTORY
    # from bootstrap.py so this works without SYSDBA.
    cur = conn.cursor()
    print(f"[onnx_setup] CREATE OR REPLACE DIRECTORY {ORACLE_DIR_NAME} AS '{CONTAINER_MODEL_DIR}'")
    try:
        cur.execute(f"CREATE OR REPLACE DIRECTORY {ORACLE_DIR_NAME} AS '{CONTAINER_MODEL_DIR}'")
    except oracledb.DatabaseError as e:
        print(
            f"[onnx_setup] FATAL: cannot create directory ({e}). "
            "AGENT needs CREATE ANY DIRECTORY; bootstrap.py grants it.",
            file=sys.stderr,
        )
        raise

    print(f"[onnx_setup] loading {ONNX_FILENAME} into Oracle as model {MODEL_NAME} …")
    OracleEmbeddings.load_onnx_model(
        conn=conn,
        dir=ORACLE_DIR_NAME,
        onnx_file=ONNX_FILENAME,
        model_name=MODEL_NAME,
    )

    # Smoke test: make sure the model produces a vector.
    cur.execute(
        f"SELECT VECTOR_EMBEDDING({MODEL_NAME} USING :t AS DATA) FROM dual",
        t="bootstrap embedding round-trip.",
    )
    vec = cur.fetchone()[0]
    print(f"✅ ONNX model {MODEL_NAME} loaded; smoke test produced {len(vec)}-dim vector.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
