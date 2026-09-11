[![Jupyter](https://img.shields.io/badge/Jupyter-Notebook-F37626?logo=jupyter&logoColor=white)](#) [![Python 3.10+](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)](#) [![oracle-vecdb](https://img.shields.io/badge/oracle-vecdb-F80000?logo=oracle&logoColor=white)](#)

# Finance Notebook Quickstarts

This directory contains two complementary oracle-vecdb notebook walkthroughs for financial account scenarios. Use the flow that matches your embedding strategy:

## finance-accounts-byov.ipynb (Bring Your Own Vectors)
- Creates a dense vector table configured for manually generated embeddings.
- Generates embeddings with `OracleVecDB.generate_embedding` and upserts them via `upsert_vectors`.
- Demonstrates vector-only queries and metadata filters (`$and`, `$eq`, `$lte`).
- Use when your application already computes embeddings or requires a custom embedding pipeline.

## finance-accounts-auto.ipynb (Hosted Model Auto-Embed)
- Creates a table with hosted model bindings using `embed_params={"model": MODEL_NAME, "embed_metadata_jsonpath": "ACCOUNT_SUMMARY"}`.
- Loads accounts with metadata-only payloads; the database generates embeddings server-side.
- Runs the same vector and metadata filtering workflow with minimal client code.
- Ideal when you want Oracle AI Database to manage embedding generation for you.

### Prerequisites
- `.env` file populated with `VECDB_REST_URL` and credentials.
- Python 3.9+ virtual environment with the `oracle-vecdb` SDK installed.
- Register the notebook kernel using the project virtual environment (e.g. `python -m ipykernel install --user --name vecdb-finance --display-name "Python (.venv finance)"`).

Each notebook includes cleanup steps to drop the demo tables; run them after experimenting to keep your environment tidy.