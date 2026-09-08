#!/usr/bin/env python3
"""Populate the LangChain OracleDB vector store used for hybrid retrieval.

Run this after model artifacts are prepared and ``PREDICCIONES_FINAL`` is loaded.
It inserts model-prediction documents plus football summary facts into an
``OracleVS`` table using ``langchain-oracledb`` and the in-database ONNX model.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from dotenv import load_dotenv

REPO = Path(__file__).resolve().parent.parent


def main() -> None:
    load_dotenv(REPO / ".env")
    from soccer_agent.memory.langchain_hybrid import (
        TABLE_NAME,
        fetch_soccer_documents,
        hybrid_search,
        load_documents_into_vector_store,
    )

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-predictions", type=int, default=2_500)
    parser.add_argument("--max-team-stats", type=int, default=250)
    parser.add_argument("--max-team-decades", type=int, default=750)
    parser.add_argument(
        "--reset",
        action="store_true",
        help=f"Drop and recreate {TABLE_NAME} before inserting.",
    )
    parser.add_argument(
        "--skip-indexes",
        action="store_true",
        help="Insert rows but skip vector/text/hybrid index creation.",
    )
    parser.add_argument(
        "--strict-indexes",
        action="store_true",
        help="Fail if any vector/text/hybrid index cannot be created.",
    )
    parser.add_argument(
        "--demo-query",
        default="Spain Brazil World Cup prediction favorite",
        help="Run one retrieval query after loading; pass an empty string to skip.",
    )
    ns = parser.parse_args()

    docs = fetch_soccer_documents(
        max_predictions=ns.max_predictions,
        max_team_stats=ns.max_team_stats,
        max_team_decades=ns.max_team_decades,
    )
    if not docs:
        raise SystemExit(
            "No documents found. Run scripts/setup_db.py and scripts/load_predictions.py first."
        )

    by_type: dict[str, int] = {}
    for doc in docs:
        doc_type = str(doc.metadata.get("doc_type", "unknown"))
        by_type[doc_type] = by_type.get(doc_type, 0) + 1

    print(f"Preparing {len(docs)} documents for {TABLE_NAME}: {by_type}")
    summary = load_documents_into_vector_store(
        docs,
        reset=ns.reset,
        create_indexes=not ns.skip_indexes,
        strict_indexes=ns.strict_indexes,
    )
    print(f"Inserted/updated {summary['inserted']} rows in {summary['table']}.")
    for status in summary["indexes"]:
        print(f"  index {status}")

    if ns.demo_query:
        print(f"\nHybrid retrieval demo for: {ns.demo_query!r}")
        for i, result in enumerate(hybrid_search(ns.demo_query, limit=3), start=1):
            doc_type = result.metadata.get("doc_type", "unknown")
            score = "n/a" if result.score is None else f"{result.score:.4f}"
            print(f"  {i}. [{doc_type}] score={score} {result.page_content[:180]}")


if __name__ == "__main__":
    main()
