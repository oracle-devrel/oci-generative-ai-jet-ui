"""Sprawl architecture connection helpers for PostgreSQL, Neo4j, MongoDB, and Qdrant."""

import os
import time


def connect_to_postgres(max_retries=3, retry_delay=5):
    """Connect to PostgreSQL with retry logic.

    Returns a psycopg2 connection configured from environment variables.
    """
    import psycopg2

    host = os.getenv("POSTGRES_HOST", "127.0.0.1")
    port = int(os.getenv("POSTGRES_PORT", "5432"))
    user = os.getenv("POSTGRES_USER", "vector")
    password = os.getenv("POSTGRES_PASSWORD", "VectorPwd_2025")
    dbname = os.getenv("POSTGRES_DB", "financedb")

    for attempt in range(1, max_retries + 1):
        try:
            print(f"  [Postgres] Connection attempt {attempt}/{max_retries}...")
            conn = psycopg2.connect(
                host=host,
                port=port,
                user=user,
                password=password,
                dbname=dbname,
            )
            conn.autocommit = False
            print("  [Postgres] Connected successfully!")
            return conn
        except psycopg2.OperationalError as e:
            print(f"  [Postgres] Connection failed (attempt {attempt}/{max_retries}): {e}")
            if attempt < max_retries:
                print(f"  [Postgres] Waiting {retry_delay}s before retry...")
                time.sleep(retry_delay)
            else:
                raise
        except Exception as e:
            print(f"  [Postgres] Unexpected error: {e}")
            raise

    raise ConnectionError("Failed to connect to PostgreSQL after all retries")


def connect_to_neo4j():
    """Connect to Neo4j Community Edition.

    Returns a neo4j Driver instance configured from environment variables.
    """
    from neo4j import GraphDatabase

    uri = os.getenv("NEO4J_URI", "bolt://127.0.0.1:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "Neo4jPwd_2025")

    try:
        print("  [Neo4j] Connecting...")
        driver = GraphDatabase.driver(uri, auth=(user, password))
        # Verify connectivity
        driver.verify_connectivity()
        print("  [Neo4j] Connected successfully!")
        return driver
    except Exception as e:
        print(f"  [Neo4j] Connection failed: {e}")
        raise


def connect_to_mongodb():
    """Connect to MongoDB Community Edition.

    Returns a tuple of (MongoClient, Database) configured from environment variables.
    """
    from pymongo import MongoClient

    uri = os.getenv("MONGO_URI", "mongodb://root:MongoPwd_2025@127.0.0.1:27017")
    db_name = os.getenv("MONGO_DB", "financedb")

    try:
        print("  [MongoDB] Connecting...")
        client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        # Verify connectivity
        client.admin.command("ping")
        db = client[db_name]
        print(f"  [MongoDB] Connected successfully! Database: {db_name}")
        return client, db
    except Exception as e:
        print(f"  [MongoDB] Connection failed: {e}")
        raise


def connect_to_qdrant():
    """Connect to Qdrant vector database.

    Returns a QdrantClient instance configured from environment variables.
    """
    from qdrant_client import QdrantClient

    host = os.getenv("QDRANT_HOST", "127.0.0.1")
    port = int(os.getenv("QDRANT_PORT", "6333"))

    try:
        print("  [Qdrant] Connecting...")
        client = QdrantClient(host=host, port=port, timeout=10)
        # Verify connectivity by listing collections
        client.get_collections()
        print(f"  [Qdrant] Connected successfully! ({host}:{port})")
        return client
    except Exception as e:
        print(f"  [Qdrant] Connection failed: {e}")
        raise


def connect_all():
    """Connect to all four sprawl databases.

    Returns a dict with keys: pg_conn, neo4j_driver, mongo_client, mongo_db, qdrant_client.
    """
    print("\n--- Connecting to sprawl databases ---")

    pg_conn = connect_to_postgres()
    neo4j_driver = connect_to_neo4j()
    mongo_client, mongo_db = connect_to_mongodb()
    qdrant_client = connect_to_qdrant()

    print("\n--- All sprawl databases connected ---\n")
    return {
        "pg_conn": pg_conn,
        "neo4j_driver": neo4j_driver,
        "mongo_client": mongo_client,
        "mongo_db": mongo_db,
        "qdrant_client": qdrant_client,
    }


def close_all(pg_conn=None, neo4j_driver=None, mongo_client=None, **kwargs):
    """Gracefully close all sprawl database connections."""
    if pg_conn:
        try:
            pg_conn.close()
            print("  [Postgres] Connection closed.")
        except Exception as e:
            print(f"  [Postgres] Error closing: {e}")

    if neo4j_driver:
        try:
            neo4j_driver.close()
            print("  [Neo4j] Driver closed.")
        except Exception as e:
            print(f"  [Neo4j] Error closing: {e}")

    if mongo_client:
        try:
            mongo_client.close()
            print("  [MongoDB] Client closed.")
        except Exception as e:
            print(f"  [MongoDB] Error closing: {e}")

    # QdrantClient does not require explicit close
    print("  [Qdrant] No explicit close needed.")
