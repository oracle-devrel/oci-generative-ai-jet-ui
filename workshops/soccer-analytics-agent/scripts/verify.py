#!/usr/bin/env python3
"""End-to-end environment verification — prints a green/red checklist.

Checks the workshop is fully wired: Oracle reachable, required tables present
with reasonable row counts, ALL_MINILM_L6_V2 returns 384-dim embeddings, and
the OCI Grok endpoint responds.
"""

from __future__ import annotations

import os
import sys

from soccer_agent.db import get_connection

CHECKS_TABLES = [
    ("MATCH_RESULTS", 49_000),
    ("GOALSCORERS", 47_000),
    ("SHOOTOUTS", 600),
    ("PREDICCIONES_FINAL", 2_500),
    ("SOCCER_LANGCHAIN_DOCS", 300),
    ("AGENT_SESSIONS", 0),
    ("SEMANTIC_MEMORY", 300),
]


def _check_oracle() -> bool:
    try:
        with get_connection() as conn:
            conn.cursor().execute("SELECT 1 FROM DUAL").fetchone()
        return True
    except Exception as exc:
        print(f"  ✗ Oracle: {exc}")
        return False


def _check_table(name: str, min_rows: int) -> bool:
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(f"SELECT COUNT(*) FROM {name}")
            n = cur.fetchone()[0]
        ok = n >= min_rows
        print(f"  {'✓' if ok else '✗'} {name}: {n} rows (need >= {min_rows})")
        return ok
    except Exception as exc:
        print(f"  ✗ {name}: {exc}")
        return False


def _check_embedding() -> bool:
    try:
        from soccer_agent.agent.embeddings import embed_one
        v = embed_one("hello")
        ok = v.shape == (384,)
        print(f"  {'✓' if ok else '✗'} ALL_MINILM_L6_V2 embed: {v.shape}")
        return ok
    except Exception as exc:
        print(f"  ✗ Embedding: {exc}")
        return False


def _check_langchain_oracledb() -> bool:
    try:
        from langchain_oracledb.vectorstores.oraclevs import OracleVS  # noqa: F401

        print("  ✓ langchain-oracledb OracleVS import")
        return True
    except Exception as exc:
        print(f"  ✗ langchain-oracledb: {exc}")
        return False


def _check_langgraph_oracledb() -> bool:
    try:
        from langgraph_oracledb.store.oracle import OracleStore  # noqa: F401
        from soccer_agent.observability.langgraph_steps import ensure_observability_store

        ensure_observability_store()
        print("  ✓ langgraph-oracledb OracleStore observability setup")
        return True
    except Exception as exc:
        print(f"  ✗ langgraph-oracledb: {exc}")
        return False


def _check_model() -> bool:
    try:
        import joblib

        from soccer_agent.inference.live import MODEL_PATH

        if not MODEL_PATH.exists():
            print(f"  ✗ best_model.pkl missing: {MODEL_PATH}")
            return False
        bundle = joblib.load(MODEL_PATH)
        features = bundle.get("features", []) if isinstance(bundle, dict) else []
        classes = set(bundle.get("classes_", [])) if isinstance(bundle, dict) else set()
        ok = len(features) == 92 and {"Win", "Draw", "Loss"} <= classes
        print(
            f"  {'✓' if ok else '✗'} best_model.pkl: "
            f"{len(features)} features, classes={sorted(classes)}"
        )
        return ok
    except Exception as exc:
        print(f"  ✗ Model artifact: {exc}")
        return False


def _check_grok() -> bool:
    if not os.environ.get("OCI_GENAI_API_KEY") or "REPLACE_ME" in os.environ.get("OCI_GENAI_API_KEY", ""):
        print("  ✗ OCI_GENAI_API_KEY not set (or placeholder)")
        return False
    if not os.environ.get("OCI_COMPARTMENT_ID") or "REPLACE_ME" in os.environ.get("OCI_COMPARTMENT_ID", ""):
        print("  ✗ OCI_COMPARTMENT_ID not set (or placeholder)")
        return False
    try:
        from soccer_agent.agent.grok_client import chat
        r = chat([{"role": "user", "content": "Reply with exactly: PONG."}])
        ok = "pong" in r.text.lower()
        print(f"  {'✓' if ok else '✗'} Grok replied: {r.text[:60]!r}")
        return ok
    except Exception as exc:
        print(f"  ✗ Grok call failed: {exc}")
        return False


def main() -> int:
    print("Loading .env ...")
    from dotenv import load_dotenv
    from pathlib import Path
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")

    fails = 0
    print("Oracle:")
    if not _check_oracle():
        return 1
    print("Tables:")
    for name, n in CHECKS_TABLES:
        if not _check_table(name, n):
            fails += 1
    print("Embedding:")
    if not _check_embedding():
        fails += 1
    print("LangChain OracleDB:")
    if not _check_langchain_oracledb():
        fails += 1
    print("LangGraph OracleDB observability:")
    if not _check_langgraph_oracledb():
        fails += 1
    print("Model:")
    if not _check_model():
        fails += 1
    print("Grok 4:")
    if not _check_grok():
        fails += 1
    print()
    if fails:
        print(f"FAILED ({fails} checks)")
        return 1
    print("All checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
