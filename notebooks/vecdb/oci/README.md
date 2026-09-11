[![Jupyter](https://img.shields.io/badge/Jupyter-Notebook-F37626?logo=jupyter&logoColor=white)](#) [![Python 3.10+](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)](#) [![oracle-vecdb](https://img.shields.io/badge/oracle-vecdb-F80000?logo=oracle&logoColor=white)](#)

# OCI Embedding Pipeline Notebook

`oci-embedding-pipeline.ipynb` demonstrates how to:
- Authenticate with OCI Generative AI, generate embeddings, and ingest them into Oracle Autonomous AI Vector Database (VECDB).
- Create or reuse vector tables, upsert batches of vectors, and run similarity queries.
- Refresh embeddings when documents change, with optional cleanup to drop demo tables.

## Prerequisites
- OCI tenancy with Generative AI service access and an embedding model ID.
- Oracle Autonomous AI Vector Database credentials stored in `.env` (host, username, password).
- Python 3.10+ environment with the packages listed in the notebook's setup cell.

Set `DROP_TABLE_WHEN_DONE=true` in your environment before running the cleanup cell if you want the demo table removed automatically.
