"""Download and register the in-database ONNX embedder.

Mirrors notebook §3.4. Steps:
  1. Confirm AGENT has CREATE MINING MODEL (granted by `agent_setup.ensure_agent_user`).
  2. Stage the model file inside the Oracle container at /opt/oracle/onnx_models/.
  3. As SYSDBA, create an Oracle directory pointing at that path; grant to AGENT.
  4. As AGENT, call DBMS_VECTOR.LOAD_ONNX_MODEL to register it.
"""

import os
import pathlib
import shutil
import subprocess
import tempfile
import urllib.error
import urllib.request
import zipfile

import oracledb


CONTAINER_NAME = os.environ.get("ORACLE_CONTAINER", "oracle-free")
CONTAINER_MODEL_DIR = "/opt/oracle/onnx_models"
ONNX_FILE = "all_MiniLM_L12_v2.onnx"
ONNX_DIRECTORY = "ONNX_DIR"
ONNX_EMBED_MODEL = "ALL_MINILM_L12_V2"

ORACLE_MODEL_URL = (
    "https://adwc4pm.objectstorage.us-ashburn-1.oci.customer-oci.com"
    "/p/TtH6hL2y25EypZ0-rrczRZ1aXp7v1ONbRBfCiT-BDBN8WLKQ3lgyW6RxCfIFLdA6"
    "/n/adwc4pm/b/OML-ai-models/o/all_MiniLM_L12_v2_augmented.zip"
)


def _container_cli() -> str:
    os.environ["PATH"] = ":".join([
        "/opt/homebrew/bin", "/usr/local/bin", "/usr/bin", "/bin",
        os.environ.get("PATH", ""),
    ])
    return "docker" if shutil.which("docker") else "podman"


def _exists_in_container(cli: str, path: str) -> bool:
    return subprocess.run(
        [cli, "exec", CONTAINER_NAME, "test", "-f", path],
        capture_output=True,
    ).returncode == 0


def _stage_in_container():
    """Download + extract + copy the ONNX file into the container."""
    cli = _container_cli()
    if not shutil.which(cli):
        raise SystemExit(
            f"Cannot find {cli!r} on PATH. Stage the ONNX file manually:\n"
            f"  1. Download {ORACLE_MODEL_URL}\n"
            f"  2. Unzip; copy the .onnx into {CONTAINER_MODEL_DIR}/{ONNX_FILE}\n"
            f"  3. Re-run bootstrap."
        )
    subprocess.run(
        [cli, "exec", CONTAINER_NAME, "mkdir", "-p", CONTAINER_MODEL_DIR],
        check=True,
    )
    target = f"{CONTAINER_MODEL_DIR}/{ONNX_FILE}"
    if _exists_in_container(cli, target):
        print(f"  '{ONNX_FILE}' already present in {CONTAINER_NAME}")
        return target

    print("  downloading Oracle augmented all-MiniLM-L12-v2 ONNX model (~117 MB)...")
    with tempfile.TemporaryDirectory() as tmp:
        zip_path = os.path.join(tmp, "model.zip")
        try:
            urllib.request.urlretrieve(ORACLE_MODEL_URL, zip_path)
        except urllib.error.URLError as e:
            raise SystemExit(
                f"Download failed: {e}. The pre-signed URL may have rotated; see "
                "https://docs.oracle.com/en/database/oracle/oracle-database/26/vecse/"
                "import-onnx-models-oracle-database-end-end-example.html"
            )
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(tmp)
        onnx_path = next(pathlib.Path(tmp).glob("*.onnx"))
        subprocess.run(
            [cli, "cp", str(onnx_path), f"{CONTAINER_NAME}:{target}"],
            check=True,
        )
        subprocess.run(
            [cli, "exec", "--user", "0", CONTAINER_NAME, "chmod", "644", target],
            check=False, capture_output=True,
        )
    print(f"  staged at {CONTAINER_NAME}:{target}")
    return target


def _ensure_directory(sys_conn, agent_user: str):
    with sys_conn.cursor() as cur:
        cur.execute(
            f"CREATE OR REPLACE DIRECTORY {ONNX_DIRECTORY} AS '{CONTAINER_MODEL_DIR}'"
        )
        cur.execute(
            f"GRANT READ, WRITE ON DIRECTORY {ONNX_DIRECTORY} TO {agent_user}"
        )
    sys_conn.commit()
    print(f"  directory {ONNX_DIRECTORY} -> {CONTAINER_MODEL_DIR} (granted to {agent_user})")


def _register_model(agent_conn):
    with agent_conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) FROM user_mining_models WHERE model_name = :m",
            m=ONNX_EMBED_MODEL,
        )
        already = cur.fetchone()[0] > 0
    if already:
        print(f"  model {ONNX_EMBED_MODEL!r} already loaded")
        return

    print(f"  loading {ONNX_EMBED_MODEL!r} from {ONNX_DIRECTORY}/{ONNX_FILE}...")
    with agent_conn.cursor() as cur:
        cur.execute(
            "BEGIN "
            "  DBMS_VECTOR.LOAD_ONNX_MODEL("
            "    directory  => :d, "
            "    file_name  => :f, "
            "    model_name => :m, "
            "    metadata   => JSON('{\"function\":\"embedding\",\"embeddingOutput\":\"embedding\",\"input\":{\"input\":[\"DATA\"]}}') "
            "  ); "
            "END;",
            d=ONNX_DIRECTORY, f=ONNX_FILE, m=ONNX_EMBED_MODEL,
        )
    agent_conn.commit()

    # Smoke test
    with agent_conn.cursor() as cur:
        cur.execute(
            f"SELECT VECTOR_EMBEDDING({ONNX_EMBED_MODEL} USING :t AS DATA) FROM dual",
            t="bootstrap embedding round-trip.",
        )
        vec = cur.fetchone()[0]
    print(f"  loaded; smoke-test produced {len(vec)}-dim vector")


def ensure_embedder(sys_conn, agent_conn, agent_user: str):
    print("Ensuring ONNX embedder...")
    _stage_in_container()
    _ensure_directory(sys_conn, agent_user)
    _register_model(agent_conn)
