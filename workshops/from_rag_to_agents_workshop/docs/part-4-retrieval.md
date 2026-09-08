# Part 4: Retrieval Mechanisms [Search Engine]

## What You Are Building

This is the core retrieval part. You will implement and compare five retrieval strategies, all running natively inside Oracle — no external search service required.

| Strategy           | Technique                                 | Best For                            |
| ------------------ | ----------------------------------------- | ----------------------------------- |
| Keyword            | Oracle Text `CONTAINS()`                  | Exact term matching                 |
| Vector             | `VECTOR_DISTANCE()` with HNSW             | Semantic similarity                 |
| Hybrid Pre-Filter  | Text filter first, then vector rank       | Known-keyword + semantic            |
| Hybrid Post-Filter | Vector candidates first, then text filter | Broad semantic + keyword refinement |
| Hybrid RRF         | Reciprocal Rank Fusion of both lists      | Balanced fusion of both signals     |
| Graph              | SQL Property Graph + vector seed          | Multi-hop relationship discovery    |

**Why multiple strategies?** No single retrieval method is best for all queries. Keyword search excels when the user knows the exact terminology. Vector search finds relevant results even when no keywords match. Hybrid combines both signals. Graph discovers connections that neither keyword nor vector search can surface alone. A production RAG system needs the right strategy for each query type.

## Keyword Search (Pre-built)

Uses the Oracle Text index to find documents where `CONTAINS(text, :keyword)` matches. Results are ranked by `SCORE(1)` — Oracle Text's built-in relevance score.

This is provided complete — read through it to understand the baseline that other strategies build on.

---

## TODO 2: Implement `vector_search_research_papers`

Write a function that performs pure semantic search:

1. Encodes the query using the embedding model with `search_query:` prefix
2. Converts the embedding to `array.array('f', ...)` for Oracle binding
3. Runs a SQL query using `VECTOR_DISTANCE(embedding, :q, COSINE)`
4. Returns `(rows, columns)` tuple

**Why `search_query:` prefix?** The nomic embedding model was trained with asymmetric prefixes (see Part 2). Using `search_query:` at retrieval time tells the model "this is a question seeking content", matching it against documents that were indexed with `search_document:`. Omitting the prefix degrades search quality.

**Key SQL pattern:**

```sql
SELECT arxiv_id, title, abstract,
       ROUND(1 - VECTOR_DISTANCE(embedding, :q, COSINE), 4) AS similarity_score
FROM research_papers
ORDER BY similarity_score DESC
FETCH APPROX FIRST :top_k ROWS ONLY WITH TARGET ACCURACY 90
```

**Why `FETCH APPROX`?** This tells Oracle to use the HNSW index for approximate search rather than exact brute-force scan. `WITH TARGET ACCURACY 90` guarantees at least 90% of the true top-k results appear in the output — a good trade-off between speed and completeness.

**Complete solution:**

```python
def vector_search_research_papers(conn, embedding_model, search_query, top_k=5):
    query_embedding = embedding_model.encode(
        [f"search_query: {search_query}"],
        convert_to_numpy=True, normalize_embeddings=True
    )[0].astype(np.float32).tolist()
    query_embedding_array = array.array('f', query_embedding)

    query = f"""
        SELECT arxiv_id, title, abstract,
               SUBSTR(text, 1, 200) AS text_snippet,
               ROUND(1 - VECTOR_DISTANCE(embedding, :q, COSINE), 4) AS similarity_score
        FROM research_papers
        ORDER BY similarity_score DESC
        FETCH APPROX FIRST {top_k} ROWS ONLY WITH TARGET ACCURACY 90
    """
    with conn.cursor() as cur:
        cur.execute(query, q=query_embedding_array)
        rows = cur.fetchall()
        columns = [desc[0] for desc in cur.description]
    return rows, columns
```

**Key concept:** `1 - VECTOR_DISTANCE(...)` converts distance to similarity. COSINE distance ranges from 0 (identical) to 2 (opposite). After the conversion, similarity ranges from -1 to 1, where 1 means identical. Ordering `DESC` puts the most similar results first.

---

## TODO 3: Implement `hybrid_search_research_papers_pre_filter`

Combine keyword filtering with vector ranking:

1. Encode the query (same as vector search)
2. Use `WHERE CONTAINS(text, :kw, 1) > 0` to pre-filter
3. Rank filtered results by `VECTOR_DISTANCE`

**Why pre-filter?** This strategy first narrows the candidate set with keywords, then re-ranks by semantic similarity. It is useful when the user's query contains a specific term that must appear in the results — for example, "transformer architecture for protein folding" should only return papers that actually mention the keyword, ranked by how semantically relevant they are.

**Complete solution:**

```python
def hybrid_search_research_papers_pre_filter(conn, embedding_model, search_phrase, top_k=10, show_explain=False):
    query_embedding = embedding_model.encode(
        [f"search_query: {search_phrase}"],
        convert_to_numpy=True, normalize_embeddings=True
    )[0].astype(np.float32).tolist()
    query_embedding_array = array.array('f', query_embedding)

    with conn.cursor() as cur:
        sql = f"""
            SELECT arxiv_id, title, abstract,
                   SUBSTR(text, 1, 200) AS text_snippet,
                   ROUND(1 - VECTOR_DISTANCE(embedding, :q, COSINE), 4) AS similarity_score
            FROM research_papers
            WHERE CONTAINS(text, :kw, 1) > 0
            ORDER BY similarity_score DESC
            FETCH APPROX FIRST {top_k} ROWS ONLY WITH TARGET ACCURACY 90
        """
        cur.execute(sql, q=query_embedding_array, kw=search_phrase)
        rows = cur.fetchall()
        columns = [desc[0] for desc in cur.description]
    return rows, columns, None
```

**Key concept:** The `WHERE CONTAINS(...)` clause runs against the Oracle Text index, and the `ORDER BY VECTOR_DISTANCE(...)` uses the HNSW index. Oracle's query optimiser handles both in a single execution plan — no two-pass logic in Python. This is a key advantage of running both search types inside the database.

---

## Hybrid Post-Filter, RRF, and Graph (Pre-built)

These are provided as complete implementations. Read through them to understand the patterns:

- **Post-filter**: retrieves vector candidates first, then applies a text filter to remove results that do not contain the keyword. Useful when you want broad semantic recall with keyword validation.
- **RRF (Reciprocal Rank Fusion)**: runs keyword and vector searches independently, then fuses their rankings with `1/(k + rank)`. Each result gets a combined score regardless of which method found it. This is the most balanced hybrid strategy.
- **Graph**: seeds from vector similarity to find an initial set of relevant papers, then expands via `SIMILAR_TO` and shared-author paths using `GRAPH_TABLE()`. This discovers papers that are not directly similar but are connected through co-authorship or topic networks.

## Compare Retrieval Strategies

The final cell runs all strategies on the same query and displays results side-by-side so you can compare ranking behaviour. Pay attention to which papers appear in one strategy but not others — this illustrates why strategy selection matters for RAG quality.

## Troubleshooting

**"ORA-29902: CONTAINS error"** — The Oracle Text index may not be synced. Run: `EXEC CTX_DDL.SYNC_INDEX('rp_text_idx')`

**Empty vector results** — Verify data was ingested: `SELECT COUNT(*) FROM research_papers`. You should see 200 rows.

**Slow vector queries** — Check that the HNSW index was created successfully. Without it, Oracle falls back to exact brute-force scan.
