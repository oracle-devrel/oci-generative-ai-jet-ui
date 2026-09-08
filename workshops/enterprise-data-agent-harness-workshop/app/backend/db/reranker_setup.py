"""Stage + register the in-database cross-encoder reranker. Mirrors §3.5 of
the notebook.

The reranker is loaded as a *regression* ONNX model with two text inputs
(DATA1=query, DATA2=document) so it can be invoked from SQL via PREDICTION():

    SELECT PREDICTION(reranker_model USING :q AS DATA1, doc AS DATA2) FROM ...

This is the second stage of the retrieval pipeline — cosine + HNSW
oversample, then PREDICTION() rerank over the top-k candidates. When no
reranker is loaded the harness gracefully falls through to cosine ordering
(see retrieval.rerank.rerank_factory).

Loading is opt-in via env:
    RERANKER_URL  — public/Drive URL for an Oracle-augmented reranker .onnx
                    (the augmentation bakes the tokenizer into the graph so
                    PREDICTION accepts raw strings).
    RERANKER_FILE — local filename inside the container (default
                    bge_reranker_base.onnx).
    RERANKER_MODEL_NAME — registered model name (default RERANKER_ONNX).

If RERANKER_URL is unset, this module is a no-op and `rerank()` becomes a
cosine-order pass-through. That's the default to keep startup fast.
"""

from __future__ import annotations

import json
import os
import pathlib
import re
import shutil
import subprocess
import tempfile
import urllib.error
import urllib.request
import zipfile

import oracledb


CONTAINER_NAME = os.environ.get("ORACLE_CONTAINER", "oracle-free")
CONTAINER_MODEL_DIR = "/opt/oracle/onnx_models"
ONNX_DIRECTORY = "ONNX_DIR"

DEFAULT_RERANKER_URL = (
    # Pre-augmented BGE-reranker-base ONNX (~275MB). Same artifact the
    # notebook §3.5 uses; the augmentation bakes in tokenization so
    # PREDICTION(... USING :q AS DATA1, :doc AS DATA2) accepts raw strings.
    "https://drive.google.com/file/d/1-xDRSHr_ulbO7MqVlWLu6ZA2J-bCjUoY/view?usp=drive_link"
)


def _container_cli() -> str | None:
    os.environ["PATH"] = ":".join([
        "/opt/homebrew/bin", "/usr/local/bin", "/usr/bin", "/bin",
        os.environ.get("PATH", ""),
    ])
    return shutil.which("docker") or shutil.which("podman")


def _exists_in_container(cli: str, container: str, path: str) -> bool:
    return subprocess.run(
        [cli, "exec", container, "test", "-f", path],
        capture_output=True,
    ).returncode == 0


def _is_loaded(agent_conn, model_name: str) -> bool:
    with agent_conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) FROM user_mining_models WHERE model_name = :m",
            m=model_name,
        )
        return cur.fetchone()[0] > 0


def ensure_reranker(agent_conn) -> dict:
    """Idempotently stage + register the reranker. Returns a status dict.

    Result keys:
        loaded     — bool: whether the model is registered after this call
        model_name — registered name (or None when loaded=False)
        reason     — short human-readable explanation when loaded=False
    """
    url = os.environ.get("RERANKER_URL", "").strip()
    if not url:
        return {"loaded": False, "model_name": None,
                "reason": "RERANKER_URL not set; rerank() will pass through."}

    file_name = os.environ.get("RERANKER_FILE", "bge_reranker_base.onnx").strip()
    model_name = os.environ.get("RERANKER_MODEL_NAME", "RERANKER_ONNX").strip()

    if _is_loaded(agent_conn, model_name):
        return {"loaded": True, "model_name": model_name,
                "reason": "already registered"}

    cli = _container_cli()
    if not cli:
        return {"loaded": False, "model_name": None,
                "reason": "neither docker nor podman on PATH; can't stage the file"}

    target = f"{CONTAINER_MODEL_DIR}/{file_name}"
    if not _exists_in_container(cli, CONTAINER_NAME, target):
        with tempfile.TemporaryDirectory() as tmp:
            local_path = os.path.join(tmp, file_name)
            drive_match = re.search(r"drive\.google\.com/.*?/d/([A-Za-z0-9_-]+)", url)
            try:
                if drive_match:
                    try:
                        import gdown
                    except ImportError:
                        return {"loaded": False, "model_name": None,
                                "reason": "Drive URL but `gdown` not installed; "
                                          "pip install gdown or use a direct URL"}
                    gdown.download(id=drive_match.group(1), output=local_path, quiet=True)
                else:
                    urllib.request.urlretrieve(url, local_path)
            except (urllib.error.URLError, Exception) as e:
                return {"loaded": False, "model_name": None,
                        "reason": f"download failed: {type(e).__name__}: {e}"}

            # Some hosts ship a zip; some ship a bare .onnx.
            if local_path.endswith(".zip"):
                with zipfile.ZipFile(local_path) as zf:
                    zf.extractall(tmp)
                cand = next(pathlib.Path(tmp).glob("*.onnx"), None)
                if cand is None:
                    return {"loaded": False, "model_name": None,
                            "reason": "no .onnx inside reranker zip"}
                src = str(cand)
            else:
                src = local_path

            subprocess.run([cli, "cp", src, f"{CONTAINER_NAME}:{target}"], check=True)
            subprocess.run(
                [cli, "exec", "--user", "0", CONTAINER_NAME, "chmod", "644", target],
                check=False, capture_output=True,
            )

    # Register the model. metadata.function='regression' + two inputs.
    rerank_meta = json.dumps({
        "function": "regression",
        "regressionOutput": "output",
        "input": {
            "first_input":  ["DATA1"],
            "second_input": ["DATA2"],
        },
    })
    try:
        with agent_conn.cursor() as cur:
            cur.execute(
                "BEGIN "
                "  DBMS_VECTOR.LOAD_ONNX_MODEL("
                "    directory  => :d, "
                "    file_name  => :f, "
                "    model_name => :m, "
                "    metadata   => JSON(:meta) "
                "  ); "
                "END;",
                d=ONNX_DIRECTORY, f=file_name, m=model_name, meta=rerank_meta,
            )
        agent_conn.commit()
    except oracledb.DatabaseError as e:
        return {"loaded": False, "model_name": None,
                "reason": f"LOAD_ONNX_MODEL failed: {e}"}

    return {"loaded": True, "model_name": model_name,
            "reason": "registered"}
