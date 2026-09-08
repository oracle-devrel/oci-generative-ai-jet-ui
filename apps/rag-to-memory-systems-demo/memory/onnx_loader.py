"""Download all-MiniLM-L12-v2 ONNX (Oracle's augmented variant) and load it into Oracle.

This runs once at setup. The model occupies ~88MB inside the DB.

The model required is an Oracle-augmented ONNX that includes pre- and post-
processing steps (tokenisation → embeddings) in a single ONNX graph. The
standard HuggingFace model.onnx will NOT work because it requires separate
tokenisation and only outputs last_hidden_state, not a pooled "embedding".

Oracle distributes the L12 augmented variant via OML AI Models object storage.
"""
from __future__ import annotations

import sys
import zipfile
from pathlib import Path
from urllib.request import urlopen

import oracledb

from memory.db import connect_sync
from memory.embeddings import MODEL_NAME, VECTOR_DIM  # noqa: F401

# Filename Oracle will look for inside DATA_PUMP_DIR
ONNX_FILE_NAME = "all_MiniLM_L12_v2.onnx"

# Local cache path (not tracked in git — add data/onnx/*.onnx to .gitignore)
LOCAL_CACHE = Path("data/onnx") / ONNX_FILE_NAME

# Oracle OML AI Models object storage — L12 augmented variant
ONNX_URL = "https://adwc4pm.objectstorage.us-ashburn-1.oci.customer-oci.com/p/TtH6hL2y25EypZ0-rrczRZ1aXp7v1ONbRBfCiT-BDBN8WLKQ3lgyW6RxCfIFLdA6/n/adwc4pm/b/OML-ai-models/o/all_MiniLM_L12_v2_augmented.zip"


def download_and_extract() -> Path:
    """Download the ONNX zip from Oracle's object storage and extract the .onnx file.

    Returns the local path to the extracted .onnx file.
    """
    LOCAL_CACHE.parent.mkdir(parents=True, exist_ok=True)

    if LOCAL_CACHE.exists():
        print(f"ONNX file already cached at {LOCAL_CACHE}")
        return LOCAL_CACHE

    zip_path = LOCAL_CACHE.parent / "all_MiniLM_L12_v2_augmented.zip"

    print(f"Downloading from {ONNX_URL} ...")
    with urlopen(ONNX_URL) as response:
        with open(zip_path, "wb") as out:
            out.write(response.read())
    print(f"Downloaded to {zip_path}")

    print(f"Extracting {ONNX_FILE_NAME} ...")
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extract(ONNX_FILE_NAME, LOCAL_CACHE.parent)

    print(f"Extracted to {LOCAL_CACHE}")
    return LOCAL_CACHE


def find_data_pump_dir(conn: oracledb.Connection) -> str:
    """Return the filesystem path of DATA_PUMP_DIR inside the container."""
    cur = conn.cursor()
    cur.execute(
        "SELECT directory_path FROM all_directories WHERE directory_name = 'DATA_PUMP_DIR'"
    )
    row = cur.fetchone()
    if not row:
        raise RuntimeError("DATA_PUMP_DIR directory not configured in Oracle")
    return row[0]


def model_already_loaded(conn: oracledb.Connection) -> bool:
    """Return True if the ONNX model is already present in the database."""
    cur = conn.cursor()
    cur.execute(
        "SELECT COUNT(*) FROM all_mining_models WHERE model_name = :name",
        name=MODEL_NAME,
    )
    (count,) = cur.fetchone()
    return count > 0


def load_into_oracle(
    file_in_data_pump_dir: str = ONNX_FILE_NAME,
    drop_existing: bool = True,
) -> None:
    """Load (or reload) the ONNX model.

    file_in_data_pump_dir is the bare filename inside DATA_PUMP_DIR
    (e.g., 'all_MiniLM_L12_v2.onnx').

    The file must already be present in DATA_PUMP_DIR before calling this.
    Copy it with:
        docker cp all_MiniLM_L12_v2.onnx oracle-free:/opt/oracle/admin/FREE/dpdump/4C9F355217A8010BE063020011AC8BA2/
    """
    conn = connect_sync()
    try:
        cur = conn.cursor()
        if drop_existing:
            try:
                cur.execute(
                    "BEGIN DBMS_VECTOR.DROP_ONNX_MODEL(:name, force => TRUE); END;",
                    name=MODEL_NAME,
                )
                conn.commit()
            except oracledb.DatabaseError:
                pass  # not yet loaded — that's fine

        cur.execute(
            """
            BEGIN
              DBMS_VECTOR.LOAD_ONNX_MODEL(
                directory  => 'DATA_PUMP_DIR',
                file_name  => :fname,
                model_name => :mname,
                metadata   => JSON('{"function":"embedding","embeddingOutput":"embedding","input":{"input":["DATA"]}}')
              );
            END;
            """,
            fname=file_in_data_pump_dir,
            mname=MODEL_NAME,
        )
        conn.commit()
        print(f"Loaded ONNX model as {MODEL_NAME} (dim={VECTOR_DIM}).")
    finally:
        conn.close()


def main() -> None:
    """CLI entry point.

    Usage:
        python -m memory.onnx_loader

    Downloads the ONNX zip from Oracle's object storage, extracts it locally,
    then provides instructions for copying it into the container's DATA_PUMP_DIR.
    """
    # Download and extract the ONNX file locally
    local_onnx = download_and_extract()

    # Find DATA_PUMP_DIR in the running Oracle database
    conn = connect_sync()
    try:
        dpdump_path = find_data_pump_dir(conn)
    finally:
        conn.close()

    print("\n" + "=" * 80)
    print("NEXT STEP: Copy the ONNX file into the container")
    print("=" * 80)
    print(f"\nRun the following command on your host machine:\n")
    print(f"  docker cp {local_onnx} oracle-free:{dpdump_path}/{ONNX_FILE_NAME}")
    print(f"\nThen re-run this command to load the model into Oracle.\n")
    print("=" * 80)


if __name__ == "__main__":
    main()
