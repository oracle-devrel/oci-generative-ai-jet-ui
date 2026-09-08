# Workshop TODO Checklist

7 hands-on tasks across Parts 3-5. Complete them in order — each builds on the last.

Parts 1 (Oracle setup) and 2 (data loading) are pre-built — just run the cells to connect and load the data.

---

### Part 1 — Oracle Setup ([Guide](part-1-oracle-setup.md))

No TODOs — pre-built. Run the cells to connect to Oracle AI Database.

### Part 2 — Data Loading ([Guide](part-2-data-loading.md))

No TODOs — pre-built. Read through to understand the data pipeline.

### Part 3 — Table Setup ([Guide](part-3-table-setup.md))

1. Write the DDL to create the `research_papers` table with safe drops (TODO 1)

### Part 4 — Retrieval ([Guide](part-4-retrieval.md))

2. Implement `keyword_search_research_papers` with Oracle Text `CONTAINS()` (TODO 2)
3. Implement `vector_search_research_papers` with `VECTOR_DISTANCE()` (TODO 3)
4. Implement `hybrid_search_research_papers_pre_filter` — keyword filter + vector rank (TODO 4)
5. Implement `hybrid_search_research_papers_postfilter` — vector candidates + keyword filter (TODO 5)
6. Implement `graph_search_research_papers` with `GRAPH_TABLE()` (TODO 6)

### Part 5 — RAG Pipeline ([Guide](part-5-rag-pipeline.md))

7. Implement `research_paper_assistant_rag_pipeline` (TODO 7)
