#!/usr/bin/env python3
"""Pre-build seed step for the supply-chain demand-planning workshop.

Runs *once* during Codespace post-create. After this script finishes the
workshop notebook can assume:

- The `harisss/Supplychain` Hugging Face dataset has been loaded and the
  top-12 products + a standing buy-volume policy live in `OracleVS`
  (table: `supplychain_demand`).
- Two planner-scoped preferences (priya = conservative, michael = aggressive)
  live in `AsyncOracleStore` under `("users", <user_id>, "memories")`.

This is idempotent: a second run wipes the supplychain_demand rows and
the agent_memory store rows before re-inserting.

Embeddings are computed **in-database** via `OracleEmbeddings` against the
`ALL_MINILM_L12_V2` ONNX model loaded by `onnx_setup.py`. No external
embedding API is called.
"""

from __future__ import annotations

import asyncio
import os
import sys
from collections import Counter, defaultdict

import oracledb
from datasets import load_dataset
from langchain_community.vectorstores.utils import DistanceStrategy
from langchain_oracledb import OracleEmbeddings, OracleVS
from langgraph_oracledb.store.oracle import AsyncOracleStore

# ─── Tunables ────────────────────────────────────────────────────────────
SAMPLE_ROWS = int(os.environ.get("SEED_SAMPLE_ROWS", "20000"))
MAX_PRODUCTS = int(os.environ.get("SEED_MAX_PRODUCTS", "12"))
VS_TABLE = os.environ.get("VS_TABLE", "supplychain_demand")
STORE_SUFFIX = os.environ.get("STORE_SUFFIX", "agent_memory")
ONNX_MODEL = os.environ.get("ONNX_EMBED_MODEL", "ALL_MINILM_L12_V2")
ONNX_DIMS = int(os.environ.get("ONNX_EMBED_DIM", "384"))


def _connect_sync():
    """Open a sync Oracle connection from env."""
    return oracledb.connect(
        user=os.environ["ORACLE_USER"],
        password=os.environ["ORACLE_PASSWORD"],
        dsn=os.environ.get("ORACLE_DSN", "localhost:1521/FREEPDB1"),
    )


async def _connect_async():
    """Open an async Oracle connection from env."""
    return await oracledb.connect_async(
        user=os.environ["ORACLE_USER"],
        password=os.environ["ORACLE_PASSWORD"],
        dsn=os.environ.get("ORACLE_DSN", "localhost:1521/FREEPDB1"),
    )


def _aggregate_top_products(rows_limit: int, max_products: int):
    """Pull a slice of harisss/Supplychain and aggregate per product."""
    print(f"[seed] downloading harisss/Supplychain[:{rows_limit}] from Hugging Face …")
    ds = load_dataset("harisss/Supplychain", split=f"train[:{rows_limit}]")

    agg: dict[str, dict] = defaultdict(
        lambda: {
            "category": None,
            "department": None,
            "visits": 0,
            "hours": Counter(),
            "dates": Counter(),
            "ips": set(),
        }
    )
    for row in ds:
        p = row["Product"]
        bucket = agg[p]
        bucket["category"] = row["Category"]
        bucket["department"] = row["Department"].strip()
        bucket["visits"] += 1
        bucket["hours"][row["Hour"]] += 1
        bucket["dates"][row["Date"].split(" ")[0]] += 1
        bucket["ips"].add(row["ip"])
    top = sorted(agg.items(), key=lambda kv: kv[1]["visits"], reverse=True)[:max_products]
    print(f"[seed] aggregated {len(agg)} unique products; keeping top {len(top)}")
    return top


def _report(name: str, b: dict) -> str:
    peak_hour, _ = b["hours"].most_common(1)[0]
    peak_date, peak_visits = b["dates"].most_common(1)[0]
    date_range = sorted(b["dates"])
    return (
        f"Demand intelligence — {name}\n"
        f"Category: {b['category']} | Department: {b['department']}\n"
        f"Window: {date_range[0]} → {date_range[-1]} ({len(date_range)} active days)\n"
        f"Total visits: {b['visits']} | Unique IPs: {len(b['ips'])}\n"
        f"Peak day: {peak_date} ({peak_visits} visits) | Peak hour: {peak_hour:02d}:00 UTC"
    )


POLICY_TEXT = (
    "Planner buy-volume policy:\n"
    "- For SKUs with fewer than 500 unique IPs in the window, recommend conservative volumes.\n"
    "- For SKUs with peak hour after 18:00 UTC, plan evening promo support.\n"
    "- Always cross-reference at least 2 historical reports before committing."
)

USER_MEMORIES = [
    (
        ("users", "priya", "memories"),
        "pref-conservative",
        {
            "note": "Priya consistently prefers conservative buy volumes and emphasises evening promo support."
        },
    ),
    (
        ("users", "michael", "memories"),
        "pref-aggressive",
        {
            "note": "Michael chases category leaders; favours aggressive stocking when comparable SKUs clear 500 unique IPs."
        },
    ),
]


def _seed_vector_store(sync_conn, top_products):
    """Truncate + re-seed `OracleVS` with demand reports + policy memo."""
    print(f"[seed] truncating + reseeding OracleVS table '{VS_TABLE}' …")
    embeddings = OracleEmbeddings(
        conn=sync_conn,
        params={"provider": "database", "model": ONNX_MODEL},
    )
    oracle_vs = OracleVS(
        client=sync_conn,
        embedding_function=embeddings,
        table_name=VS_TABLE,
        distance_strategy=DistanceStrategy.COSINE,
    )
    # Idempotent: clear any rows left from prior runs.
    try:
        cur = sync_conn.cursor()
        cur.execute(f"DELETE FROM {VS_TABLE}")
        sync_conn.commit()
    except oracledb.DatabaseError:
        # Table doesn't exist yet — first add_texts will create it.
        pass

    texts = [_report(name, b) for name, b in top_products]
    metadatas = [{"type": "demand_report", "product": name} for name, _ in top_products]
    texts.append(POLICY_TEXT)
    metadatas.append({"type": "policy", "name": "planner_buy_volume"})
    oracle_vs.add_texts(texts, metadatas=metadatas)
    print(f"[seed] OracleVS: {len(texts)} documents written")


async def _seed_long_term_store(top_products):
    """Truncate + re-seed `AsyncOracleStore` with user-scoped memories."""
    print(f"[seed] reseeding AsyncOracleStore (table_suffix='{STORE_SUFFIX}') …")
    async_conn = await _connect_async()

    # Use OpenAI-free path: embeddings via the *same* in-DB ONNX model the
    # sync vector store uses, wrapped in OracleEmbeddings with a fresh
    # sync connection (the store's index config keeps a reference, so we
    # need a connection it can use independently).
    sync_conn_for_store = _connect_sync()
    embeddings = OracleEmbeddings(
        conn=sync_conn_for_store,
        params={"provider": "database", "model": ONNX_MODEL},
    )

    store = AsyncOracleStore(
        async_conn,
        index={
            "dims": ONNX_DIMS,
            "embed": embeddings,
            "fields": ["note"],
            "index_type": {"type": "hnsw", "distance_metric": "COSINE"},
        },
        table_suffix=STORE_SUFFIX,
    )
    await store.setup()

    # Idempotent: delete any prior memories under our namespaces.
    for namespace, key, _ in USER_MEMORIES:
        try:
            await store.adelete(namespace, key)
        except Exception:
            pass

    for namespace, key, value in USER_MEMORIES:
        await store.aput(namespace, key, value)
    print(f"[seed] AsyncOracleStore: {len(USER_MEMORIES)} user memories written")

    await async_conn.close()
    sync_conn_for_store.close()


def main() -> int:
    print("=" * 60)
    print("Supply-chain demand-planning workshop — seed step")
    print("=" * 60)

    # Sanity: the AGENT user must exist and the ONNX model must be loaded.
    sync_conn = _connect_sync()
    cur = sync_conn.cursor()
    cur.execute(
        "SELECT COUNT(*) FROM user_mining_models WHERE model_name = :n",
        n=ONNX_MODEL,
    )
    (count,) = cur.fetchone()
    if count == 0:
        print(
            f"[seed] FATAL: ONNX model {ONNX_MODEL!r} is not loaded in this schema. "
            "Run app/scripts/onnx_setup.py first.",
            file=sys.stderr,
        )
        return 2

    top_products = _aggregate_top_products(SAMPLE_ROWS, MAX_PRODUCTS)
    _seed_vector_store(sync_conn, top_products)
    sync_conn.close()

    asyncio.run(_seed_long_term_store(top_products))

    print()
    print("✅ Seed complete. The workshop notebook can now run end-to-end.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
