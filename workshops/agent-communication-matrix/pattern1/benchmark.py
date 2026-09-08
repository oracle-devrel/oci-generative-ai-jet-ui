"""Pattern 1 benchmark: measure MCP tool-call round-trip latency.

For each query in QUERIES:
  1. Get a 768-dim embedding from Ollama (measure: embed_ms)
  2. Run a VECTOR_DISTANCE query against kb_chunks (measure: search_ms)
  3. Capture total wall-clock time (measure: total_ms)

Reports median and p95 across all runs.

Usage:
    python pattern1/benchmark.py
"""
import array
import asyncio
import os
import statistics
import time

import httpx
import oracledb
from dotenv import load_dotenv

load_dotenv()

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
EMBED_MODEL = os.environ.get("EMBED_MODEL", "nomic-embed-text")

# Representative queries the benchmark will issue.
# Variety matters more than realism here; the embedding cost is roughly
# constant per call regardless of query content.
QUERIES = [
    "How does vector search work in Oracle Database?",
    "What is at-least-once delivery?",
    "Explain the difference between MCP and A2A.",
    "When should I use a message queue instead of REST?",
    "What is the agent communication matrix?",
    "How do typed tool schemas help LLM agents?",
    "What are the trade-offs of payload-by-reference?",
    "How does Oracle AI Database handle vector indexing?",
    "What is back-pressure in queue-based systems?",
    "When is REST still the right protocol for agents?",
    "How do dead-letter queues handle poison messages?",
    "What is the role of audit trails in agent governance?",
    "Why does observability matter for multi-agent systems?",
    "How does the MCP discovery layer change agent behavior?",
    "What does at-most-once delivery mean in practice?",
    "When should I introduce A2A instead of MCP?",
    "How do I migrate from REST APIs to MCP servers?",
    "What is the cost of additional protocol surface area?",
    "How does multi-tenancy affect agent architecture?",
    "What is the tool/agent boundary problem?",
]

# Number of repetitions per query. Total runs = len(QUERIES) * RUNS_PER_QUERY.
RUNS_PER_QUERY = 5

# Number of warmup queries to discard. First calls hit cold connection pools,
# JIT, and HTTP keep-alive setup; including them skews the median.
WARMUP_RUNS = 3


pool = oracledb.create_pool(
    user=os.environ["DB_USER"],
    password=os.environ["DB_PASS"],
    dsn=os.environ["DB_DSN"],
    min=1,
    max=4,
)


async def embed(client: httpx.AsyncClient, text: str) -> tuple[list[float], float]:
    """Embed a text and return (vector, elapsed_ms)."""
    start = time.perf_counter()
    response = await client.post(
        f"{OLLAMA_URL}/api/embeddings",
        json={"model": EMBED_MODEL, "prompt": text},
        timeout=60.0,
    )
    response.raise_for_status()
    elapsed_ms = (time.perf_counter() - start) * 1000
    return response.json()["embedding"], elapsed_ms


def vector_search(vec_list: list[float], k: int = 5) -> tuple[list, float]:
    """Run a vector search and return (results, elapsed_ms)."""
    vec = array.array("f", vec_list)
    start = time.perf_counter()
    with pool.acquire() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT chunk_text FROM kb_chunks
            ORDER BY VECTOR_DISTANCE(embedding, :q, COSINE)
            FETCH FIRST :k ROWS ONLY
            """,
            q=vec,
            k=k,
        )
        results = cur.fetchall()
    elapsed_ms = (time.perf_counter() - start) * 1000
    return results, elapsed_ms


def percentile(data: list[float], p: float) -> float:
    """Return the p-th percentile (0-100) using nearest-rank method."""
    if not data:
        return 0.0
    sorted_data = sorted(data)
    k = int(len(sorted_data) * (p / 100.0))
    k = min(k, len(sorted_data) - 1)
    return sorted_data[k]


async def main() -> None:
    embed_times: list[float] = []
    search_times: list[float] = []
    total_times: list[float] = []

    async with httpx.AsyncClient() as client:
        # Warmup. Throw away these measurements.
        print(f"Warming up ({WARMUP_RUNS} queries)...")
        for q in QUERIES[:WARMUP_RUNS]:
            vec, _ = await embed(client, q)
            vector_search(vec)

        # Actual benchmark.
        total_runs = len(QUERIES) * RUNS_PER_QUERY
        print(
            f"Running benchmark: {len(QUERIES)} queries x {RUNS_PER_QUERY} runs = {total_runs} measurements\n"
        )

        for i, q in enumerate(QUERIES):
            for run in range(RUNS_PER_QUERY):
                total_start = time.perf_counter()
                vec, embed_ms = await embed(client, q)
                _, search_ms = vector_search(vec)
                total_ms = (time.perf_counter() - total_start) * 1000

                embed_times.append(embed_ms)
                search_times.append(search_ms)
                total_times.append(total_ms)

            print(f"  Query {i + 1}/{len(QUERIES)} done")

    # Report.
    print("\n" + "=" * 60)
    print(f"Results across {len(total_times)} runs:")
    print("=" * 60)
    print(f"Embedding ({EMBED_MODEL}):")
    print(f"  median: {statistics.median(embed_times):6.1f} ms")
    print(f"  p95:    {percentile(embed_times, 95):6.1f} ms")
    print(f"  min:    {min(embed_times):6.1f} ms")
    print(f"  max:    {max(embed_times):6.1f} ms")
    print("\nOracle vector search:")
    print(f"  median: {statistics.median(search_times):6.1f} ms")
    print(f"  p95:    {percentile(search_times, 95):6.1f} ms")
    print(f"  min:    {min(search_times):6.1f} ms")
    print(f"  max:    {max(search_times):6.1f} ms")
    print("\nTotal round-trip:")
    print(f"  median: {statistics.median(total_times):6.1f} ms")
    print(f"  p95:    {percentile(total_times, 95):6.1f} ms")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
