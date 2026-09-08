#!/usr/bin/env python3
"""Run database setup and seed data."""

import os
import shutil
import subprocess
import sys

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from config import EMBEDDING_MODEL_NAME  # noqa: E402
from database.connection import connect_to_oracle  # noqa: E402
from database.seed import run_full_seed  # noqa: E402
from database.setup import create_user_if_needed, run_full_setup  # noqa: E402

ORACLE_CONTAINER_NAME = "oracle-ai-demo"


def check_docker_ready():
    """Check that Docker is running and the Oracle container is available."""
    docker_bin = shutil.which("docker")
    if docker_bin is None:
        print("ERROR: Docker is not installed (or not on your PATH).")
        print("  Install Docker Desktop from https://www.docker.com/products/docker-desktop")
        sys.exit(1)

    # Check if the Docker daemon is responsive
    try:
        subprocess.run(
            ["docker", "info"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=10,
        )
    except (subprocess.SubprocessError, OSError):
        print("ERROR: Docker daemon is not running.")
        print("  Please start Docker Desktop and wait for it to be ready, then re-run this script.")
        sys.exit(1)

    # Check if the Oracle container exists and is running
    result = subprocess.run(
        ["docker", "inspect", "-f", "{{.State.Status}}", ORACLE_CONTAINER_NAME],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"ERROR: Container '{ORACLE_CONTAINER_NAME}' not found.")
        print("  Start it with:  docker compose up -d")
        sys.exit(1)

    status = result.stdout.strip()
    if status != "running":
        print(
            f"ERROR: Container '{ORACLE_CONTAINER_NAME}' exists but is not running (status: {status})."
        )
        print("  Start it with:  docker compose up -d")
        sys.exit(1)

    print(f"  Docker is running and container '{ORACLE_CONTAINER_NAME}' is up.\n")


def main():
    print("=== AFSA - Database Setup & Seed ===\n")

    # Pre-flight: make sure Docker + Oracle container are available
    print("Checking Docker environment...")
    check_docker_ready()

    # Load embedding model
    print("Loading embedding model...")
    from langchain_huggingface import HuggingFaceEmbeddings

    embedding_model = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL_NAME)
    print(f"  Model loaded: {EMBEDDING_MODEL_NAME}\n")

    # Create the VECTOR user first (connects as SYSDBA)
    print("Creating database user if needed...")
    create_user_if_needed()

    # Now connect as the VECTOR user
    print("\nConnecting to Oracle Database...")
    conn = connect_to_oracle()

    # Run setup (tables, indexes, graph)
    print("\n--- Running database schema setup ---")
    stores = run_full_setup(conn, embedding_model, skip_user_creation=True)

    # Run seed
    print("\n--- Seeding demo data ---")
    knowledge_base_vs = stores["KNOWLEDGE_BASE"]
    run_full_seed(conn, knowledge_base_vs)

    conn.close()
    print("\n=== All done! ===")


if __name__ == "__main__":
    main()
