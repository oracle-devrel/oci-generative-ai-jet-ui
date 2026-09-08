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

---

## TODO 2: Implement `keyword_search_research_papers`

Write a function that performs full-text keyword search:

1. Write a SQL query using `CONTAINS(text, :keyword, 1) > 0` to match documents
2. Rank results by `SCORE(1)` — Oracle Text's built-in relevance score
3. Include `SUBSTR(text, 1, 200)` as a text snippet
4. Limit to `FETCH FIRST 10 ROWS ONLY`
5. Return `(rows, columns)` tuple

**Why `CONTAINS()` instead of `LIKE`?** `CONTAINS()` uses the Oracle Text index you created in Part 3. It supports stemming, fuzzy matching, and relevance scoring — far more powerful than a simple `LIKE '%keyword%'` which scans every row and has no ranking.

**Key SQL pattern:**

```sql
SELECT arxiv_id, title, SUBSTR(text, 1, 200) AS text_snippet,
       SCORE(1) AS relevance_score
FROM research_papers
WHERE CONTAINS(text, :keyword, 1) > 0
ORDER BY SCORE(1) DESC
FETCH FIRST 10 ROWS ONLY
```

**Why `SCORE(1)`?** The `1` in `CONTAINS(text, :keyword, 1)` is a label. `SCORE(1)` returns the relevance score for that label. Higher scores mean the keyword appears more prominently in the document.

**Complete solution:**

```python
def keyword_search_research_papers(conn, keyword: str):
    """Perform a full-text keyword search using the Oracle Text index."""
    query = """
        SELECT arxiv_id, title, SUBSTR(text, 1, 200) AS text_snippet,
               SCORE(1) AS relevance_score
        FROM research_papers
        WHERE CONTAINS(text, :keyword, 1) > 0
        ORDER BY SCORE(1) DESC
        FETCH FIRST 10 ROWS ONLY
    """
    with conn.cursor() as cur:
        cur.execute(query, keyword=keyword)
        rows = cur.fetchall()
        columns = [desc[0] for desc in cur.description]
    return rows, columns
```

**Key concept:** This is the simplest retrieval strategy — pure lexical matching. It serves as your baseline. Every other strategy in this part builds on or complements it.

---

## TODO 3: Implement `vector_search_research_papers`

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

## TODO 4: Implement `hybrid_search_research_papers_pre_filter`

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

## TODO 5: Implement `hybrid_search_research_papers_postfilter`

Reverse the pre-filter approach — get vector candidates first, then apply a keyword filter:

1. Encode the query (same as vector search)
2. Use a CTE (`WITH vec_candidates AS ...`) to retrieve the top `candidate_k` results by vector distance
3. Apply `WHERE CONTAINS(text, :kw, 1) > 0` on the CTE to filter down
4. Return `(rows, columns, None)` tuple

**Why post-filter?** Pre-filter can miss semantically relevant papers that use different terminology. Post-filter casts a wider semantic net first, then validates with keywords. It is useful when you want broad recall but need keyword confirmation — for example, ensuring the paper actually discusses "BERT" rather than just being topically related.

**Key SQL pattern:**

```sql
WITH vec_candidates AS (
    SELECT arxiv_id, title, abstract, text,
           1 - VECTOR_DISTANCE(embedding, :q, COSINE) AS similarity_score
    FROM research_papers
    ORDER BY similarity_score DESC
    FETCH APPROX FIRST :candidate_k ROWS ONLY WITH TARGET ACCURACY 90
)
SELECT arxiv_id, title,
       SUBSTR(text, 1, 200) AS text_snippet,
       ROUND(similarity_score, 4) AS similarity_score
FROM vec_candidates
WHERE CONTAINS(text, :kw, 1) > 0
ORDER BY similarity_score DESC
FETCH FIRST :top_k ROWS ONLY
```

**Complete solution:**

```python
def hybrid_search_research_papers_postfilter(
    conn, embedding_model, search_phrase: str,
    top_k: int = 10, candidate_k: int = 200, show_explain: bool = False
):
    """Hybrid search: vector candidates first, then text filter."""
    query_embedding = embedding_model.encode(
        [f"search_query: {search_phrase}"],
        convert_to_numpy=True, normalize_embeddings=True
    )[0].astype(np.float32).tolist()
    query_embedding_array = array.array('f', query_embedding)

    with conn.cursor() as cur:
        sql = f"""
            WITH vec_candidates AS (
                SELECT arxiv_id, title, abstract, text,
                       1 - VECTOR_DISTANCE(embedding, :q, COSINE) AS similarity_score
                FROM research_papers
                ORDER BY similarity_score DESC
                FETCH APPROX FIRST {candidate_k} ROWS ONLY WITH TARGET ACCURACY 90
            )
            SELECT arxiv_id, title,
                   SUBSTR(text, 1, 200) AS text_snippet,
                   ROUND(similarity_score, 4) AS similarity_score
            FROM vec_candidates
            WHERE CONTAINS(text, :kw, 1) > 0
            ORDER BY similarity_score DESC
            FETCH FIRST {top_k} ROWS ONLY
        """
        cur.execute(sql, q=query_embedding_array, kw=search_phrase)
        rows = cur.fetchall()
        columns = [desc[0] for desc in cur.description]
    return rows, columns, None
```

**Key concept:** The CTE approach means Oracle first uses the HNSW index to get a broad set of vector candidates, then applies the Oracle Text filter on that smaller set. This is the inverse of pre-filtering — broader semantic recall with keyword validation.

---

## TODO 6: Implement `graph_search_research_papers`

Combine vector similarity with graph traversal:

1. Encode the query and retrieve top `seed_k` papers by vector distance (the "seed set")
2. Expand via `GRAPH_TABLE()` on `SIMILAR_TO` edges to find topically related papers
3. Expand via `GRAPH_TABLE()` on shared-author paths (`Paper <- WROTE - Author - WROTE -> Paper`)
4. `UNION ALL` the seed hits, similarity hops, and author hops
5. Score each candidate with weighted combination of seed score and edge score
6. Return `(rows, columns)` tuple

**Why graph retrieval?** Vector and keyword search find papers that are directly relevant to the query. Graph retrieval discovers papers that are _indirectly_ relevant — connected through co-authorship networks or topic similarity chains. A paper by the same author on a related subtopic may not rank highly in vector search but is often exactly what a researcher needs.

**Key SQL pattern:**

```sql
WITH seed AS (
    SELECT arxiv_id, 1 - VECTOR_DISTANCE(embedding, :q, COSINE) AS seed_score
    FROM research_papers
    ORDER BY seed_score DESC
    FETCH APPROX FIRST :seed_k ROWS ONLY WITH TARGET ACCURACY 90
),
sim_hops AS (
    SELECT s.arxiv_id AS source_arxiv_id, gt.target_arxid AS candidate_arxiv_id, ...
    FROM seed s
    JOIN GRAPH_TABLE(
        research_graph
        MATCH (src IS paper)-[e IS similar_to]->(dst IS paper)
        COLUMNS (src.arxiv_id AS source_arxiv_id, dst.arxiv_id AS target_arxiv_id, e.sim_score AS edge_score)
    ) gt ON gt.source_arxiv_id = s.arxiv_id
),
...
```

**Complete solution:**

```python
def graph_search_research_papers(
    conn, embedding_model, search_query: str, top_k: int = 10, seed_k: int = 25
):
    """Graph retrieval using Oracle SQL Property Graph + GRAPH_TABLE."""
    seed_k = max(seed_k, top_k)
    query_embedding = embedding_model.encode(
        [f"search_query: {search_query}"],
        convert_to_numpy=True, normalize_embeddings=True
    )[0].astype(np.float32).tolist()
    query_embedding_array = array.array('f', query_embedding)

    sql = f"""
        WITH seed AS (
            SELECT arxiv_id, 1 - VECTOR_DISTANCE(embedding, :q, COSINE) AS seed_score
            FROM research_papers
            ORDER BY seed_score DESC
            FETCH APPROX FIRST {seed_k} ROWS ONLY WITH TARGET ACCURACY 90
        ),
        seed_hits AS (
            SELECT arxiv_id AS source_arxiv_id, arxiv_id AS candidate_arxiv_id,
                   seed_score, 'seed' AS relation_type, seed_score AS edge_score
            FROM seed
        ),
        sim_hops AS (
            SELECT s.arxiv_id AS source_arxiv_id, gt.target_arxiv_id AS candidate_arxiv_id,
                   s.seed_score, 'similar_to' AS relation_type, gt.edge_score AS edge_score
            FROM seed s
            JOIN GRAPH_TABLE(
                research_graph
                MATCH (src IS paper)-[e IS similar_to]->(dst IS paper)
                COLUMNS (src.arxiv_id AS source_arxiv_id, dst.arxiv_id AS target_arxiv_id, e.sim_score AS edge_score)
            ) gt ON gt.source_arxiv_id = s.arxiv_id
        ),
        author_hops AS (
            SELECT s.arxiv_id AS source_arxiv_id, gt.target_arxiv_id AS candidate_arxiv_id,
                   s.seed_score, 'shared_author' AS relation_type, 1.0 AS edge_score
            FROM seed s
            JOIN GRAPH_TABLE(
                research_graph
                MATCH (src IS paper)<-[w1 IS wrote]-(a IS author)-[w2 IS wrote]->(dst IS paper)
                COLUMNS (src.arxiv_id AS source_arxiv_id, dst.arxiv_id AS target_arxiv_id)
            ) gt ON gt.source_arxiv_id = s.arxiv_id
            WHERE gt.target_arxiv_id <> s.arxiv_id
        ),
        candidates AS (
            SELECT * FROM seed_hits UNION ALL
            SELECT * FROM sim_hops UNION ALL
            SELECT * FROM author_hops
        ),
        scored AS (
            SELECT candidate_arxiv_id AS arxiv_id,
                   MAX(CASE relation_type
                       WHEN 'seed' THEN seed_score
                       WHEN 'similar_to' THEN (0.70 * seed_score) + (0.30 * edge_score)
                       WHEN 'shared_author' THEN (0.85 * seed_score) + (0.15 * edge_score)
                       ELSE seed_score END) AS graph_score
            FROM candidates GROUP BY candidate_arxiv_id
        )
        SELECT rp.arxiv_id, rp.title, rp.abstract,
               SUBSTR(rp.text, 1, 200) AS text_snippet,
               ROUND(sc.graph_score, 4) AS graph_score
        FROM scored sc JOIN research_papers rp ON rp.arxiv_id = sc.arxiv_id
        ORDER BY graph_score DESC
        FETCH FIRST {top_k} ROWS ONLY
    """
    with conn.cursor() as cur:
        cur.execute(sql, q=query_embedding_array)
        rows = cur.fetchall()
        columns = [desc[0] for desc in cur.description]
    return rows, columns
```

**Key concept:** Graph retrieval is the most powerful strategy here because it combines three signals: direct vector similarity (seed), topic proximity (SIMILAR_TO edges), and social proximity (shared authorship). The weighted scoring formula balances these signals — you can tune the weights for your domain.

---

## Reciprocal Rank Fusion (Pre-built)

RRF is provided as a complete implementation. Read through it to understand the pattern — it runs keyword and vector searches independently, then fuses their rankings with `1/(k + rank)`. Each result gets a combined score regardless of which method found it.

## Compare Retrieval Strategies

The final cell runs all strategies on the same query and displays results side-by-side so you can compare ranking behaviour. Pay attention to which papers appear in one strategy but not others — this illustrates why strategy selection matters for RAG quality.

## Troubleshooting

**"ORA-29902: CONTAINS error"** — The Oracle Text index may not be synced. Run: `EXEC CTX_DDL.SYNC_INDEX('rp_text_idx')`

**Empty vector results** — Verify data was ingested: `SELECT COUNT(*) FROM research_papers`. You should see 200 rows.

**Slow vector queries** — Check that the HNSW index was created successfully. Without it, Oracle falls back to exact brute-force scan.
