[![Jupyter](https://img.shields.io/badge/Jupyter-Notebook-F37626?logo=jupyter&logoColor=white)](#) [![Python 3.10+](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)](#) [![oracle-vecdb](https://img.shields.io/badge/oracle-vecdb-F80000?logo=oracle&logoColor=white)](#)

# Private AI Services Container (PASC) Integration Quickstart

The Oracle Private AI Services Container is a robust, secure AI infrastructure for regulated organizations that need private instances of AI models without sharing data with third-party providers. It can be deployed in a customer tenancy in the public cloud, on private clouds, or on-premises, including air-gapped environments. For access and download instructions, see https://www.oracle.com/database/private_ai_services_container/.

`private_ai_services_container_integration.ipynb` demonstrates the full Private AI Services Container + Oracle VecDB workflow: extract text from Oracle documentation pages, generate embeddings with a Private AI Services Container, and store/search vectors in a BYOV table.

## What You'll Do
1. Install dependencies.
2. Define a Private AI Services Container embeddings client.
3. Configure VecDB + Private AI Services Container connections.
4. Create a BYOV vector table.
5. Build documentation extraction + chunking helpers.
6. Ingest docs (embed + upsert).
7. Query for answers.
8. (Optional) Clean up the table.

## Prerequisites
- Oracle VecDB endpoint and credentials.
- Access to a Private AI Services Container embeddings endpoint and API key.
- Python 3.10+ with the packages below installed.
- A `.env` file discoverable by `python-dotenv` (the notebook resolves the nearest `.env`).

## Install Dependencies
```bash
pip install requests python-dotenv oracle-vecdb beautifulsoup4 langchain-text-splitters
```

## Environment Variables
Copy `.env.example` to `.env` and replace values:

| Variable | Purpose |
| --- | --- |
| `VECDB_REST_URL` | VecDB REST endpoint URL. |
| `VECDB_USERNAME` | VecDB username (or `VECDB_USER`). |
| `VECDB_PASSWORD` | VecDB password. |
| `VECDB_SELF_SIGNED_SSL` | Set `true` to disable SSL verification for self-signed certs. |
| `PASC_HOST` | Base URL for the PASC embeddings service. |
| `PASC_API_KEY` | API key for the PASC embeddings endpoint. |
| `PASC_CERT` | Path to the PEM/CRT file used for TLS verification. |
| `PASC_MODEL` | Embedding model name exposed by PASC. |
| `DROP_TABLE_WHEN_DONE` | Optional: set `true` to drop the vector table after running. |
| `HTTP_PROXY` | Optional: proxy for outbound HTTP traffic. |
| `HTTPS_PROXY` | Optional: proxy for outbound HTTPS traffic. |
| `NO_PROXY` | Optional: comma-separated hosts that bypass proxies. |

## Notebook Flow Highlights
- **Private AI Services Container client**: a minimal wrapper around `POST /v1/embeddings` with API key auth.
- **VecDB config**: uses `oracle-vecdb` `Configuration` and supports self-signed SSL via `VECDB_SELF_SIGNED_SSL`.
- **BYOV table**: created with manual indexing (`index_params={"indexing": "manual"}`).
- **Chunking**: uses a LangChain `RecursiveCharacterTextSplitter` for optimized chunks.
- **Ingestion**: fetches the Generative AI overview doc, builds vectors with metadata (`source`, `chunk_index`, `content`), then upserts.
- **Querying**: embeds questions, runs VecDB `query`, and prints the top-k matching chunks.

## Workflow Summary
1. Configure `~/.env` with VecDB and Private AI Services Container credentials.
2. Update `doc_urls` in the notebook to point at the docs you want to ingest.
3. Run the notebook to fetch documentation, chunk content, generate embeddings, and upsert vectors.
4. Run the query section to retrieve answers from the vector table.
5. (Optional) set `DROP_TABLE_WHEN_DONE=true` to remove the table after the run.

## Notes
- `find_dotenv()` is used, so the notebook resolves the nearest `.env` by default.
- BYOV tables are created with manual indexing—schedule indexing jobs after large upserts.
## Network / Proxy
If you need proxy to access `docs.oracle.com`. Set `HTTP_PROXY`/`HTTPS_PROXY`/`NO_PROXY` in `.env` and the notebook will normalize them for requests.
