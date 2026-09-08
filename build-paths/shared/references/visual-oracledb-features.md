# Oracle AI Database — feature catalog

Frozen snapshot of the curated feature list from https://jasperan.github.io/visual-oracledb/. Each feature has a one-paragraph "what" + a "when to use it" line. The skills cite this file when the README needs a "Why Oracle" paragraph or when the user is browsing for a project topic.

If the source site changes meaningfully, update this file by hand — don't fetch live.

---

## AI Vector Search

**What.** Native `VECTOR(dim, type)` columns and `VECTOR_DISTANCE(...)` SQL operators. HNSW-style indexes via `ORGANIZATION INMEMORY NEIGHBOR GRAPH`. No external vector DB needed.

**When to use.** Any time you need semantic search, RAG retrieval, "more like this," or clustering — and you'd rather keep one DB than wire in Pinecone/Chroma/Qdrant.

**Path tier.** Beginner (via `langchain-oracledb`). Intermediate. Advanced.

---

## In-Database ONNX Embeddings

**What.** Register a HuggingFace sentence-transformer (exported to ONNX) directly in the database via `DBMS_VECTOR.LOAD_ONNX_MODEL`. Then `VECTOR_EMBEDDING(model_name USING text)` produces vectors inside SQL — no external embedding API.

**When to use.** Data sensitivity / no-data-egress requirements. Or when you want sub-millisecond embedding latency by skipping the Python round-trip.

**Path tier.** Advanced.

---

## Hybrid Search (Vector + Lexical)

**What.** Combine `VECTOR_DISTANCE` with `CONTAINS()` (Oracle Text full-text) in one query. Three patterns: pre-filter, post-filter, RRF.

**When to use.** When pure vector recall misses on rare named entities (product SKUs, error codes, person names) that lexical search nails.

**Path tier.** Intermediate (via `EnsembleRetriever`). Advanced (raw SQL).

---

## JSON Duality Views

**What.** A view that exposes a relational schema as a nested JSON document, *with full read-write support in both directions*. Writes go to the underlying tables; reads can use either the JSON shape or the relational shape.

**When to use.** When the agent wants nested JSON (LLMs produce it natively) and the dashboard wants flat rows (BI is row-shaped). Eliminates ETL between document and relational worlds.

**Path tier.** Advanced.

---

## Property Graph (SQL/PGQ)

**What.** Tables of entities and edges, plus SQL/PGQ syntax for graph queries — n-hop neighborhoods, path matching, pattern queries.

**When to use.** Knowledge graphs, agent reasoning over typed relationships, citations / dependencies / co-occurrence networks.

**Path tier.** Advanced. (Skill prefers Python BFS over recursive CTE for bidirectional graphs — see `property-graph.md`.)

---

## Agent Memory in the Database

**What.** Oracle as the single backing store for conversational memory, knowledge bases, workflow state, tool execution logs, entity memory, and summary memory. All vector-searchable.

**When to use.** When you're building autonomous agents and want one durable, queryable backend instead of stitching Redis + Postgres + a vector DB + a JSON file.

**Path tier.** Advanced.

---

## Oracle Text (Full-Text / Lexical Search)

**What.** Real lexical search with `CONTAINS()`, `SCORE()`, BM25-style ranking. Indexes built once via `INDEXTYPE IS CTXSYS.CONTEXT`.

**When to use.** Hybrid search, exact-phrase queries, regulatory / compliance data where you can't afford to miss a literal mention.

**Path tier.** Intermediate (combined with vector). Advanced.

---

## Multi-Modal: JSON, Vector, Graph, Spatial in One DB

**What.** A single database supports relational tables, JSON documents (and JSON Duality), vector columns, graph queries, and spatial / geo all on the same schema. Cross-feature queries work.

**When to use.** Anywhere a project's domain has multiple data shapes — and you'd rather keep one engine than three.

**Path tier.** Advanced (the "DB-as-only-store" hard rule rides on this).

---

## Free Container Image (26ai Free)

**What.** `container-registry.oracle.com/database/free` — the full database, with all 26ai features (vector, JSON Duality, graph, ONNX), as a single Docker image. ~2GB, boots in ~90 seconds, persists via volume.

**When to use.** Always, for local development, learning, demos, and CI. The `build-paths` skill set assumes this is the database the user is running.

**Path tier.** All paths.

---

## Generative AI Integration (OCI GenAI)

**What.** OCI Generative AI service (Grok 4, Cohere, Llama 3.3) accessible via the OCI Python SDK *and* an OpenAI-compatible REST endpoint. Pairs naturally with Oracle AI Vector Search for RAG.

**When to use.** When you want hosted inference without leaving the Oracle universe — or when you want OpenAI-shape Python code (`from openai import OpenAI`) but on Oracle infrastructure.

**Path tier.** Intermediate. Advanced.

---

## How the skills use this catalog

- The README "Why Oracle" paragraph is auto-assembled from the entries the project actually uses (e.g. an intermediate PDF-RAG pulls vector search + hybrid search + GenAI).
- The advanced "DevDay-style demo" project literally asks the user to pick 3 features from this list and build a demo that shows them off.
- The list is intentionally short. If a feature isn't here, the skills don't pretend it is.
