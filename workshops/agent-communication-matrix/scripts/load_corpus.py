"""Load the synthetic corpus into Oracle AI Database with embeddings.

For each chunk in data/chunks.txt:
  1. Call Ollama to produce a 768-dimensional embedding.
  2. Insert the chunk and embedding into kb_chunks.

The embedding is converted to a typed float32 array.array before binding,
which is what python-oracledb expects for VECTOR columns. A plain Python
list[float] will fail with ORA-01484.

Usage:
    python scripts/load_corpus.py
"""
import array
import asyncio
import os
from pathlib import Path

import httpx
import oracledb
from dotenv import load_dotenv

load_dotenv()  # reads .env from the current working directory

# How many chunks to load. Use a smaller default for interactive demos.
# Increase to 1000 or 10000 for full benchmarks.
CHUNK_LIMIT = 100

# Commit every N rows for visible progress and reasonable transaction size.
COMMIT_EVERY = 100

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
EMBED_MODEL = os.environ.get("EMBED_MODEL", "nomic-embed-text")


pool = oracledb.create_pool(
    user=os.environ["DB_USER"],
    password=os.environ["DB_PASS"],
    dsn=os.environ["DB_DSN"],
    min=1,
    max=4,
)


async def embed(client: httpx.AsyncClient, text: str) -> list[float]:
    """Get a 768-dim embedding from Ollama."""
    # Ollama embedding endpoint uses /api/embed and returns 'embeddings' list
    response = await client.post(
        f"{OLLAMA_URL}/api/embed",
        json={"model": EMBED_MODEL, "input": text},
        timeout=60.0,
    )
    response.raise_for_status()
    return response.json()["embeddings"][0]


async def main() -> None:
    corpus_path = Path("data/chunks.txt")
    if not corpus_path.exists():
        raise SystemExit(
            "data/chunks.txt not found. Run scripts/generate_synthetic_corpus.py first."
        )

    all_chunks = corpus_path.read_text().splitlines()
    chunks = all_chunks[:CHUNK_LIMIT]
    print(f"Loading {len(chunks):,} chunks (of {len(all_chunks):,} available)...")

    # Reuse one httpx client and one Oracle connection for the whole load.
    async with httpx.AsyncClient() as client:
        with pool.acquire() as conn, conn.cursor() as cur:
            for i, chunk in enumerate(chunks):
                # 1. Get the embedding from Ollama.
                vec_list = await embed(client, chunk)

                # 2. Verify dimension matches what the table expects.
                if i == 0 and len(vec_list) != 768:
                    raise SystemExit(
                        f"Expected 768-dim embedding from {EMBED_MODEL}, "
                        f"got {len(vec_list)}. Check the model is correct."
                    )

                # 3. Convert to typed float32 array for VECTOR binding.
                #    'f' is the array module's code for 4-byte float.
                vec = array.array("f", vec_list)

                # 4. Insert. Note the SQL does NOT call VECTOR() on the bind;
                #    the driver handles conversion via the typed array.
                cur.execute(
                    """
                    INSERT INTO kb_chunks (doc_id, chunk_text, embedding)
                    VALUES (:doc, :txt, :vec)
                    """,
                    doc=f"doc_{i // 100}",
                    txt=chunk,
                    vec=vec,
                )

                if (i + 1) % COMMIT_EVERY == 0:
                    conn.commit()
                    print(f"  Loaded {i + 1:,}/{len(chunks):,}")

            conn.commit()

    print(f"\nDone. {len(chunks):,} chunks loaded into kb_chunks.")


if __name__ == "__main__":
    asyncio.run(main())
