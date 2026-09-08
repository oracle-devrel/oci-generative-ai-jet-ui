# Oracle AI Vector Search — what's under `OracleVS`

For beginner / intermediate users who stay inside `langchain-oracledb`, this file is FYI. For advanced users writing their own SQL, this is the spec.

## Vector columns

```sql
CREATE TABLE my_docs (
    id        NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    content   CLOB,
    metadata  JSON,
    embedding VECTOR(768, FLOAT32)
);
```

- `VECTOR(dim, datatype)` — `dim` must match your embedder. `nomic-embed-text` → 768, Cohere `embed-english-v3.0` → 1024, `text-embedding-3-small` → 1536.
- Datatypes: `FLOAT32` (default, what you want), `FLOAT64`, `INT8` (quantised), `BINARY`. Stay on `FLOAT32` unless storage is the bottleneck.
- `VECTOR(*, *)` is allowed (no dim/type pinning) but the skill never uses it — too easy to insert mismatched dims silently.

Requires Oracle 23ai or 26ai. The 26ai Free container has it on by default.

## Vector indexes

```sql
CREATE VECTOR INDEX my_docs_embedding_idx
ON my_docs (embedding)
ORGANIZATION INMEMORY NEIGHBOR GRAPH
WITH DISTANCE COSINE
WITH TARGET ACCURACY 95;
```

- **`INMEMORY NEIGHBOR GRAPH`** is the HNSW-style index. Fast queries, larger memory footprint. Default choice for the skills.
- **Distance metrics**: `COSINE`, `EUCLIDEAN`, `DOT`, `MANHATTAN`, `L1`, `L2_SQUARED`, `HAMMING`. The skill uses `COSINE` unless told otherwise.
- **`TARGET ACCURACY 95`** = recall target for approximate search. 95 is a sane default; bump to 99 for high-stakes retrieval, drop to 80 for "I just want it fast."
- **Free-tier limits**: vector index size is capped on the free DB. For toy / single-user workloads it's invisible; for million-doc demos, the skill warns.

Source: `~/git/personal/cAST-efficient-ollama/src/cast_ollama/oracle_db/{schema,operations}.py`.

## Similarity SQL

### Top-K, no index

```sql
SELECT id, content
FROM my_docs
ORDER BY VECTOR_DISTANCE(embedding, :qv, COSINE)
FETCH FIRST :k ROWS ONLY;
```

Exact, slow on big tables. Fine for < 10k rows.

### Top-K, with index (approximate)

```sql
SELECT id, content
FROM my_docs
ORDER BY VECTOR_DISTANCE(embedding, :qv, COSINE)
FETCH APPROX FIRST :k ROWS ONLY WITH TARGET ACCURACY 90;
```

`FETCH APPROX` activates the index. `WITH TARGET ACCURACY` is per-query — overrides the index default if you want a sharper or fuzzier hit for this one query.

### Similarity score (0-1, higher = better) for COSINE

```sql
SELECT id, content,
       ROUND(1 - VECTOR_DISTANCE(embedding, :qv, COSINE), 4) AS score
FROM my_docs
ORDER BY score DESC
FETCH FIRST :k ROWS ONLY;
```

Source: `apps/finance-ai-agent-demo/backend/retrieval/vector_search.py`.

## In-DB embeddings (advanced — no external API)

Once you've registered an ONNX model via `DBMS_VECTOR.LOAD_ONNX_MODEL` (see `onnx-in-db-embeddings.md`):

```sql
SELECT VECTOR_EMBEDDING(my_onnx_model USING 'hello world' AS data) AS v
FROM dual;
```

You can embed inside the database, on insert, with no Python round-trip:

```sql
INSERT INTO my_docs (content, embedding)
VALUES (:content, VECTOR_EMBEDDING(my_onnx_model USING :content AS data));
```

This is the path the advanced skill teaches when "no external embedding API" is a hard requirement.

## Hybrid search → see `hybrid-search.md`

Three patterns: pre-filter (CONTAINS first, vector rank), post-filter (vector first, CONTAINS scope), RRF (rank fusion). All three live in `apps/finance-ai-agent-demo/backend/retrieval/hybrid_search.py:1-80`.

## Capacity planning rule of thumb

- 1M rows × 768-dim FLOAT32 ≈ 3 GB embeddings + index overhead. Free tier handles this. Don't promise more.
- Embedding generation is usually slower than the DB. Batch your `embed_documents` calls (LangChain does this automatically; raw users should do it manually).
