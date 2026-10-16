"""
Smoke test: verify Python can query 26ai vector search end to end.
Run: python smoke_test.py
"""

import array
import os
import sys

import oracledb
from sentence_transformers import SentenceTransformer

_REQUIRED_ENV = ("ORACLE_USER", "ORACLE_PASSWORD", "ORACLE_DSN")
_missing = [v for v in _REQUIRED_ENV if v not in os.environ]
if _missing:
    sys.exit(f"ERROR: missing environment variables: {', '.join(_missing)}")

DB_USER = os.environ["ORACLE_USER"]
DB_PASSWORD = os.environ["ORACLE_PASSWORD"]
DB_DSN = os.environ["ORACLE_DSN"]

EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

QUESTION = "Why did FastAPI adopt Pydantic v2?"


def main():
    print(f"Loading model: {EMBED_MODEL}")
    model = SentenceTransformer(EMBED_MODEL)

    print(f"Encoding question: {QUESTION}")
    vec = array.array("f", model.encode(QUESTION, normalize_embeddings=True).tolist())

    print(f"Connecting to {DB_DSN} ...")
    conn = oracledb.connect(user=DB_USER, password=DB_PASSWORD, dsn=DB_DSN)
    cur = conn.cursor()

    print("Running vector search ...\n")
    cur.execute(
        """
        SELECT sha, commit_date, subject
        FROM FASTAPI_COMMITS
        ORDER BY VECTOR_DISTANCE(embedding, :1, COSINE)
        FETCH FIRST 5 ROWS ONLY
    """,
        [vec],
    )

    print(f"{'#':<4} {'SHA':<12} {'DATE':<22} {'SUBJECT'}")
    print("-" * 90)
    for i, (sha, dt, subject) in enumerate(cur, 1):
        short_sha = sha[:10]
        date_str = dt.strftime("%Y-%m-%d %H:%M") if dt else "unknown"
        print(f"{i:<4} {short_sha:<12} {date_str:<22} {subject[:60]}")

    cur.close()
    conn.close()
    print("\nSmoke test passed.")


if __name__ == "__main__":
    main()
