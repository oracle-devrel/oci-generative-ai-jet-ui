# Hybrid search — vector + lexical

For users who outgrow pure-vector recall. Three patterns, each with a use case. The intermediate skill defaults to the LangChain ensemble approach (no SQL writing); the advanced skill drops to raw SQL when control matters.

## When to use which

| Pattern | Best when | Cost |
| --- | --- | --- |
| **LangChain `EnsembleRetriever`** | You're already in LangChain and want a one-liner. | BM25 retriever holds all docs in memory. |
| **Pre-filter (SQL)** | You have a strong keyword signal and want to *only* vector-rank inside that subset. | Two-step query, bigger plan. |
| **Post-filter (SQL)** | Vector recall is the primary signal; you just want to scope by keyword. | Cheaper than pre-filter usually. |
| **RRF (SQL)** | You want a fused score where neither signal dominates. | Two queries + a fusion calc. |

## Pattern A — `EnsembleRetriever` (intermediate default)

```python
from langchain.retrievers import EnsembleRetriever, BM25Retriever
from langchain_oracledb import OracleVS

vector_r = vs.as_retriever(search_kwargs={"k": 10})

# BM25 over the same corpus — load once at startup.
bm25_r = BM25Retriever.from_documents(all_docs)
bm25_r.k = 10

hybrid = EnsembleRetriever(
    retrievers=[vector_r, bm25_r],
    weights=[0.6, 0.4],   # tune by hand; 0.6/0.4 is a sane default
)

docs = hybrid.invoke("multi-factor authentication policy")
```

**Pros.** No SQL. Drop-in to any chain that takes a retriever.
**Cons.** BM25 holds all docs in memory — won't scale past ~100k chunks. The vector branch hits Oracle; the lexical branch doesn't.

## Pattern B — Pre-filter (SQL)

Use when "definitely contains 'invoice'" is a hard requirement.

```sql
SELECT id, content
FROM (
    SELECT id, content, embedding
    FROM my_docs
    WHERE CONTAINS(content, :keyword) > 0
)
ORDER BY VECTOR_DISTANCE(embedding, :qv, COSINE)
FETCH FIRST :k ROWS ONLY;
```

Requires an Oracle Text index on `content`:
```sql
CREATE INDEX my_docs_content_idx ON my_docs(content) INDEXTYPE IS CTXSYS.CONTEXT;
```

The vector index won't be used inside the filtered subquery — the optimizer falls back to exact distance over the candidate set. That's usually fine because the filter cuts the search space hard.

## Pattern C — Post-filter (SQL)

Use when vector recall is primary; keyword is just a scope.

```sql
SELECT id, content
FROM (
    SELECT id, content, VECTOR_DISTANCE(embedding, :qv, COSINE) AS d
    FROM my_docs
    ORDER BY d
    FETCH APPROX FIRST 50 ROWS ONLY WITH TARGET ACCURACY 90
)
WHERE CONTAINS(content, :keyword) > 0
ORDER BY d
FETCH FIRST :k ROWS ONLY;
```

The inner query uses the vector index (`FETCH APPROX`); the outer filter scopes it. Cheaper than pre-filter when the keyword has many matches.

## Pattern D — RRF (Reciprocal Rank Fusion, SQL)

Use when you want both signals weighted, no clear winner.

```sql
WITH
vector_hits AS (
    SELECT id, ROW_NUMBER() OVER (ORDER BY VECTOR_DISTANCE(embedding, :qv, COSINE)) AS rnk
    FROM my_docs
    FETCH APPROX FIRST 50 ROWS ONLY WITH TARGET ACCURACY 90
),
text_hits AS (
    SELECT id, ROW_NUMBER() OVER (ORDER BY SCORE(1) DESC) AS rnk
    FROM my_docs WHERE CONTAINS(content, :keyword, 1) > 0
    FETCH FIRST 50 ROWS ONLY
)
SELECT id, SUM(1.0/(60 + rnk)) AS rrf
FROM (
    SELECT id, rnk FROM vector_hits
    UNION ALL
    SELECT id, rnk FROM text_hits
)
GROUP BY id
ORDER BY rrf DESC
FETCH FIRST :k ROWS ONLY;
```

`60` is the standard RRF k-constant. Bumping it makes the fusion gentler.

## Vector binds — the gotcha

Patterns B-D pass `:qv` as a vector. Don't bind a Python list — use `array.array("f", values)`. From `apps/finance-ai-agent-demo/backend/retrieval/hybrid_search.py:1-80`:

```python
import array
qv = array.array("f", embedder.embed_query(query))  # length must match column dim
cur.execute(sql, qv=qv, keyword=query, k=5)
```

## Don't combine LangChain `EnsembleRetriever` with raw SQL hybrid

Pick a layer. Layering both means you're paying for BM25 in memory *and* Oracle Text in the DB. The intermediate skill picks Pattern A by default; users who want raw SQL drop to Patterns B-D and skip the ensemble.

## Exemplar

`apps/finance-ai-agent-demo/backend/retrieval/hybrid_search.py:1-80` — all three SQL patterns with bind-variable handling.
