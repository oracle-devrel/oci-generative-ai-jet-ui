# Sample Notebooks

Explore these AI Database vector development notebooks for guided workflows that showcase ingestion, querying, and evaluation patterns.

For Python development with AI Database vector APIs, see the [Oracle VecDB Python SDK](https://github.com/oracle/vecdb-python-sdk).

| Title | Stack | Highlights | Path |
| ----- | ----- | ---------- | ---- |
| Quickstart: Build Vector Search with Python | AI Database vector APIs, Python | Create an integrated-embedding table, load sample records, and run a semantic search from end to end. | [Open](./start_here/quickstart.ipynb) |
| Connect to Oracle AI Database with Python | AI Database vector APIs, Python | Configure username and password or OAuth 2.0 authentication, verify the connection, and review TLS, proxy, and retry options. | [Open](./start_here/connect.ipynb) |
| Finance Accounts Auto | AI Database vector APIs, Python, Pandas | Use hosted embedding models to vectorize financial account metadata automatically and query with filters. | [Open](./finance/finance-accounts-auto.ipynb) |
| Finance Accounts BYOV | AI Database vector APIs, Python, Pandas, SentenceTransformers | Generate embeddings locally, upsert vectors, and run similarity plus metadata-filtered searches. | [Open](./finance/finance-accounts-byov.ipynb) |
| Parks Demo | AI Database vector APIs, Python, Pandas | Inspect vector table stats and execute similarity queries on the National Parks dataset, with cleanup steps. | [Open](./parks/parks-demo.ipynb) |
| Search Diagnostics | AI Database vector APIs, Python, Pandas | Explore seeded marketing data, compound filters, and vector API debug payloads for semantic search. | [Open](./search/search-diagnostics.ipynb) |
| Embedding Ingest Patterns | AI Database vector APIs, Python, Pandas, SentenceTransformers | Compare auto-embedding tables and bring-your-own embeddings while batching ingest workloads. | [Open](./embeddings/embedding-ingest-patterns.ipynb) |
| In-database Reranking | AI Database vector APIs, Hugging Face, Python, Docker/Podman, OML4Py, OCI CLI, OCI Object Storage | Download a Hugging Face model, convert and validate it as ONNX, upload it to OCI Object Storage, load it into Oracle AI Database, and run in-database reranking. | [Open](./reranking/load-model-for-in-database-reranking.ipynb) |
| OCI Generative AI Reranking | AI Database vector APIs, OCI Generative AI, Python, Pandas | Run VecDB search and rerank the returned candidates with an OCI-hosted reranking model. | [Open](./reranking/oci-reranking.ipynb) |
| Maintenance Indexing Playbook | AI Database vector APIs, Python, Pandas | Schedule background indexing jobs, monitor vector table health, and clean up archived partitions. | [Open](./maintenance/maintenance-indexing.ipynb) |
| Gemini Vector RAG | AI Database vector APIs, Google Gemini, Python, Pandas | Combine semantic retrieval with Gemini model completions to deliver grounded RAG answers. | [Open](./gemini/gemini-vecdb-rag.ipynb) |
| OCI Embedding Pipeline | AI Database vector APIs, OCI Generative AI, Python, Pandas | Call OCI Generative AI for embeddings, persist vectors, and refresh/query the dataset end to end. | [Open](./oci/oci-embedding-pipeline.ipynb) |
| HNSW Index Tuning | AI Database vector APIs, Python, SentenceTransformers | Build an explicit HNSW index, monitor vector jobs, and demonstrate how `efsearch` controls candidate beam width per query. | [Open](./index_model/hnsw-efsearch-demo.ipynb) |
| Index & Model Workbench | AI Database vector APIs, Python, Pandas | Manage index lifecycle, inspect hosted models, and capture annotation governance patterns in one workflow. | [Open](./index_model/index-model-workbench.ipynb) |
| Bulk Loading & Listings | AI Database vector APIs, Python, Pandas | Demonstrate the three bulk-ingest flows—integrated embeddings, BYO vectors with manual IDs, and BYO vectors with auto IDs—while monitoring load jobs and listing results. | [Open](./bulk_loading/) |
| Private AI Services Container Integration | AI Database vector APIs, Private AI Services Container, Python | Generate embeddings with a private AI services endpoint, store vectors in a BYOV table, and query Oracle documentation chunks. | [Open](./private_ai_service_container/private_ai_services_container_integration.ipynb) |

Need full application samples? Visit the [Sample Apps](../../apps/vecdb) catalog.
