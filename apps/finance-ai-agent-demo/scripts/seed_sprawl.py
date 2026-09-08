#!/usr/bin/env python3
"""Seed the sprawl architecture databases with sample financial data.

Usage:
    cd backend && python -m scripts.seed_sprawl
    # or from project root:
    cd backend && python ../scripts/seed_sprawl.py
"""
import os
import sys

# Ensure backend is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from database.sprawl_connection import close_all, connect_all  # noqa: E402
from database.sprawl_seed import run_sprawl_seed  # noqa: E402
from database.sprawl_setup import run_full_sprawl_setup  # noqa: E402
from langchain_huggingface import HuggingFaceEmbeddings  # noqa: E402


def main():
    print("=== Sprawl Architecture: Setup & Seed ===\n")

    # 1. Connect
    conns = connect_all()

    # 2. Setup schemas
    print("\n--- Schema Setup ---")
    run_full_sprawl_setup(
        conns["pg_conn"],
        conns["neo4j_driver"],
        conns["mongo_db"],
        conns["qdrant_client"],
    )

    # 3. Load embedding model
    print("\n--- Loading embedding model ---")
    embedding_model = HuggingFaceEmbeddings(
        model_name="sentence-transformers/paraphrase-mpnet-base-v2"
    )
    print("  Embedding model loaded.")

    # 4. Seed data
    print("\n--- Seeding Data ---")
    run_sprawl_seed(
        conns["pg_conn"],
        conns["neo4j_driver"],
        conns["mongo_db"],
        conns["qdrant_client"],
        embedding_model,
    )

    # 5. Cleanup
    close_all(**conns)
    print("\n=== Done! ===")


if __name__ == "__main__":
    main()
