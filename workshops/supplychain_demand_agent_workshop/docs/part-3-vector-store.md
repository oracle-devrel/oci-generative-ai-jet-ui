# Part 3 — `OracleVS` — the vector knowledge base

## What it is

`OracleVS` (from `langchain_oracledb`) is the canonical LangChain vector
store backed by Oracle AI Database. One table holds the `id`, the
embedding, the metadata, and the raw text; queries are vector-similarity
searches.

The pre-built `supplychain_demand` table holds **13 documents**:

| Count | `metadata.type`   | What it is                                                                          |
| ----- | ----------------- | ----------------------------------------------------------------------------------- |
| 12    | `"demand_report"` | One short narrative per top product (visits, unique IPs, peak hour/day, date range) |
| 1     | `"policy"`        | The standing buy-volume policy memo                                                 |

The 12 demand reports were aggregated from a 20 000-row slice of
`harisss/Supplychain` (HF) by `app/scripts/seed_supplychain.py`. Every
text was embedded in-database (Part 2) on the way in.

## Re-instantiating an existing table is safe

You're not seeding anything in this part — the data is already there.
You're just getting a Python handle:

```python
oracle_vs = OracleVS(
    client=oracle_client,
    embedding_function=embeddings,
    table_name="supplychain_demand",
    distance_strategy=DistanceStrategy.COSINE,
)
```

Re-instantiating an `OracleVS` against an existing table is
**non-destructive**: no `DROP`, no truncate. You just get a handle you
can query.

## What you'll use it for

Two patterns dominate this notebook:

1. **Semantic search by text.** `oracle_vs.similarity_search("soccer
merchandise demand", k=5)` returns the five closest documents by
   cosine similarity, regardless of which words the documents actually
   used. That's what gives Part 7 (the aha moment) its punch.

2. **Filter by metadata in Python.** `OracleVS` returns `Document`
   objects with `.metadata`, so you can post-filter for `type ==
"demand_report"` or `type == "policy"`:

   ```python
   all_hits = oracle_vs.similarity_search("demand", k=50)
   reports  = [h for h in all_hits if (h.metadata or {}).get("type") == "demand_report"]
   ```

In Part 8 the `demand_analyst` will use semantic search to find
historical comparables for whatever category the planner asks about.
In Part 9 the `policy_agent` will use a targeted similarity search to
fetch the standing policy memo by name.

## What you'll build in TODO 2

Construct `oracle_vs` per the snippet above. The hard-stop checkpoint
fires a `similarity_search("planner buy volume policy", k=1)` and
asserts the result contains the policy memo. If the seed step didn't
run, you'll get zero rows back and the assert will fail loudly.

## Solution

Drop this into the TODO 2 cell, replacing the `oracle_vs = None` line:

```python
from langchain_community.vectorstores.utils import DistanceStrategy
from langchain_oracledb import OracleVS

oracle_vs = OracleVS(
    client=oracle_client,
    embedding_function=embeddings,
    table_name="supplychain_demand",
    distance_strategy=DistanceStrategy.COSINE,
)
```

## Distance metric — why cosine?

Sentence-transformer embeddings (including `ALL_MINILM_L12_V2`) are
normalized to unit length, so cosine and dot-product distances are
equivalent up to sign. Cosine is the conventional default; HNSW indexes
in Oracle are optimised for it.

## Next

→ **[Part 4 — `AsyncOracleStore`](part-4-store.md)** — the _other_ Oracle persistence layer (and why it's distinct from this one).
