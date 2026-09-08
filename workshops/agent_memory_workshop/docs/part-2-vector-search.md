# Part 2: Vector Search With Langchain and Oracle AI Database

## What Is Vector Search?

Traditional SQL search matches exact values: `WHERE title = 'neural networks'`. Vector search matches meaning: given a query, find the documents whose semantic content is most similar — even if they share no keywords with the query.

The process is:

1. Convert text to a numeric vector (embedding) using a language model
2. Store vectors in a vector-enabled SQL table
3. At query time, embed the query and find stored vectors with the smallest distance

Oracle AI Database handles steps 2 and 3 natively. LangChain's `OracleVS` class handles the Python interface.

## The Embedding Model

The notebook uses `sentence-transformers/paraphrase-mpnet-base-v2`, a 768-dimensional sentence embedding model. It runs locally — no API key required. On first use it downloads ~420MB and caches it.

```python
from langchain_huggingface import HuggingFaceEmbeddings

embedding_model = HuggingFaceEmbeddings(
    model_name="sentence-transformers/paraphrase-mpnet-base-v2"
)
```

> ⏳ **The first time this cell runs it downloads ~420MB.** This can take 2-5 minutes in Codespaces. The model is cached after the first download so subsequent runs are instant.

---

## TODO 1: Initialise OracleVS

`OracleVS` is a LangChain abstraction that manages a vector-enabled SQL table in Oracle. When you initialise it, it creates the table if it does not exist and connects the embedding model.

**Complete solution:**

```python
from langchain_oracledb.vectorstores import OracleVS
from langchain_oracledb.vectorstores.oraclevs import create_index
from langchain_community.vectorstores.utils import DistanceStrategy

vector_store = OracleVS(
    client=vector_conn,
    embedding_function=embedding_model,
    table_name="VECTOR_SEARCH_DEMO",
    distance_strategy=DistanceStrategy.COSINE,
)
```

**Why `COSINE` distance?** Cosine distance measures the angle between vectors, ignoring magnitude. It works well for text embeddings because it focuses on directional similarity — two documents about the same topic point in the same direction in embedding space regardless of length.

## The HNSW Index

After creating the store, the notebook creates an HNSW index:

```python
safe_create_index(vector_conn, vector_store, "oravs_hnsw")
```

HNSW (Hierarchical Navigable Small World) is a graph-based approximate nearest-neighbour algorithm. Without it, Oracle scans every vector on every query (exact but slow). With it, queries are approximate but fast — typically milliseconds at millions of vectors.

The `safe_create_index` helper skips index creation if the index already exists, so you can safely re-run cells.

---

## TODO 2: Dataset Ingestion — Append to the Three Lists

Inside the loop, three parallel lists need to be populated for each paper. They must stay in sync — index `i` in each list always refers to the same paper.

**Why three separate lists?**

- `texts` — the content that gets embedded into a vector. Only title and abstract go here — you want the vector to represent _meaning_, not metadata like IDs or author names.
- `metadata` — the identifiers that come back when you search, so you know which paper matched.
- `sampled_papers` — the full raw record kept for reuse elsewhere in the notebook (for example seeding the knowledge base memory in Part 3).

**Complete solution:**

```python
    sampled_papers.append({
        "arxiv_id": arxiv_id,
        "title": title,
        "abstract": abstract,
        "primary_subject": primary_subject,
        "authors": authors_text,
    })
    texts.append(text)
    metadata.append({
        "id": arxiv_id,
        "arxiv_id": arxiv_id,
        "title": title,
        "primary_subject": primary_subject,
        "authors": authors_text,
    })
```

**What happens after the loop:** `vector_store.add_texts(texts=texts, metadatas=metadata)` passes all 200 texts through the HuggingFace embedding model and inserts each vector alongside its metadata into Oracle. After this cell completes, the `VECTOR_SEARCH_DEMO` table contains 200 rows — each a searchable research paper.

> ⏳ **This cell takes 1-3 minutes.** The embedding model processes each paper and Oracle inserts 200 vectors. There is no progress bar — it will complete silently and print the confirmation message when done.

---

## TODO 3: Basic Similarity Search

**Complete solution:**

```python
query = "Find research papers about planetary exploration mission planning."

results = vector_store.similarity_search(query, k=3)

for i, doc in enumerate(results, start=1):
    print(f"--- Result {i} ---")
    print("Text:", doc.page_content)
    print("Metadata:", doc.metadata)
```

`k=3` returns the 3 most similar documents. The query does not need to match any words in the documents — it finds papers whose _meaning_ is closest to the query.

---

## TODO 4: Similarity Search with Relevance Scores

**Complete solution:**

```python
results = vector_store.similarity_search_with_score(query, k=3)

for doc, score in results:
    print("Score:", score)
    print("Text :", doc.page_content)
    print("Meta :", doc.metadata)
    print("------")
```

**Score interpretation:** OracleVS returns cosine distance. The range is 0.0 to 2.0. Lower is better:

| Score     | Meaning           |
| --------- | ----------------- |
| 0.0       | Identical meaning |
| 0.0 – 0.3 | Highly relevant   |
| 0.3 – 0.7 | Related           |
| 0.7+      | Weak or no match  |

---

## Filtered Similarity Search

The next two cells demonstrate metadata filtering — combining semantic similarity with exact SQL-style filters.

The first cell (filter by subject) is pre-built. The second cell has a TODO for you to complete.

**Pre-built — Filter by exact metadata value:**

```python
docs = vector_store.similarity_search(
    query,
    k=3,
    filter={"primary_subject": {"$eq": sample_primary_subject}},
)
```

---

## TODO 5: Filter by id list ($in)

**Complete solution:**

```python
docs = vector_store.similarity_search(
    query="Explain key themes in this research paper",
    k=5,
    filter={"id": {"$in": [sample_arxiv_id]}},
)
```

**What `$in` does:** restricts the search to documents whose `id` field appears in the provided list. Passing a single ID effectively pins the search to one specific paper. You could pass multiple IDs to restrict to a set: `{"id": {"$in": [id1, id2, id3]}}`.

**Why this matters for agent memory:** an agent that remembers a specific paper from an earlier turn can retrieve it back into context using its ID — without writing a separate SQL query. The vector search pipeline handles both semantic retrieval and exact lookup through the same interface.

This is one of Oracle's key advantages: metadata filtering runs as SQL predicates inside Oracle, not as a post-processing step in Python. It is fast and consistent.

---

## Troubleshooting

**Embedding model download hangs** — The model downloads on first use over the Codespaces network. If it stalls, interrupt the cell and re-run.

`**ORA-51962: vector memory area is out of space`\*\* — The Oracle vector memory pool is too small. Run this in the terminal (no restart needed):

```bash
python3 -c "
import oracledb
conn = oracledb.connect(user='sys', password='OraclePwd_2025', dsn='localhost:1521/FREE', mode=oracledb.SYSDBA)
conn.cursor().execute('ALTER SYSTEM SET vector_memory_size = 1G SCOPE=BOTH')
conn.commit(); conn.close()
"
```

`**ORA-00955: name is already used**` — An index already exists from a previous run. `safe_create_index` handles this automatically.

**Empty search results** — The dataset ingestion cell (Step 2) must complete successfully before querying. Check it printed the ✅ confirmation message.
