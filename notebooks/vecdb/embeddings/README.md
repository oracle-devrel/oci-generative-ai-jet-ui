[![Jupyter](https://img.shields.io/badge/Jupyter-Notebook-F37626?logo=jupyter&logoColor=white)](#) [![Python 3.10+](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)](#) [![oracle-vecdb](https://img.shields.io/badge/oracle-vecdb-F80000?logo=oracle&logoColor=white)](#)

# Embedding & Ingest Patterns

`embedding-ingest-patterns.ipynb` showcases every embedding surface in Oracle VecDB using the Python SDK. The notebook includes detailed narrative markdown and console messaging that explain each stage of the workflow.

## What this notebook demonstrates
- Load environment secrets and construct an `OracleVecDB` client once for the full session.
- Configure demo table names, sample marketing copy, and model selections, echoing each decision for viewers.
- Compare BYOV ingest, auto-embedding tables, and batch embedding calls with a compact pattern skeleton and comparison table.
- Generate embeddings locally with `SentenceTransformer` (bring-your-own, or BYOV) and upsert vectors with metadata via `upsert_vectors`.
- Reset and seed a BYOV demo table, displaying the payload that lands in VecDB.
- Run semantic vector queries against the BYOV table, logging match counts and distances while previewing the DataFrame output.
- Provision an auto-embedding table with `embed_params`, showing the targeted VecDB-hosted model.
- Stream raw documents into the auto-embedding table, confirm configuration with `describe_vector_table`, and execute plain-text queries.
- Call `generate_embedding` for batch inference without persisting rows and verify dimensionality of the returned vectors.
- Drop demo resources at the end so repeated runs stay idempotent.

## Prerequisites
- `.env` containing `VECDB_REST_URL`, `VECDB_USERNAME`/`VECDB_USER`, `VECDB_PASSWORD`, and optional overrides for `EMBED_MODEL_NAME`, `EMBED_BYOV_TABLE`, `EMBED_AUTO_TABLE`, and `EMBED_HF_MODEL_NAME`.
- Python 3.10+ with the following packages (installed by the first cell if missing): `oracle-vecdb`, `python-dotenv`, `pandas`, `sentence-transformers`.
- Outbound access to your VecDB endpoint and any HuggingFace model downloads required for BYOV.

## Section-by-section walkthrough
1. **Environment & Connection** – Loads `.env`, prints resolved host/user, and constructs `OracleVecDB`, noting SSL bypass or `ADE_TEST_RUN` toggles when applicable.
2. **Constants & Samples** – Prints the BYOV and auto-embedding table names plus the count of marketing snippets used throughout the demo. Model choices are surfaced for both hosted and local runs, followed by a compact pattern skeleton.
3. **BYOV Embeddings** – Loads the specified SentenceTransformer model, drops any existing table, recreates it with annotations, seeds vectors, and previews the ingested metadata.
4. **BYOV Query** – Encodes a sample query, runs `query` with a manual vector, logs match totals and human-friendly snippets, and renders a summary DataFrame.
5. **Auto-Embedding Table** – Creates a table with `embed_params`, logging the selected VecDB model and surfacing errors that indicate unavailable hosted embeddings.
6. **Auto-Embed Ingest & Query** – Inserts raw documents (no client embeddings), inspects table description to highlight configuration, then performs text-only search and prints the top matches.
7. **Batch Embedding Endpoint** – Invokes `generate_embedding` over the seed batch, confirming response size and sample dimensionality for validation.
8. **Cleanup** – Drops both demo tables with clear console confirmation so the notebook remains repeatable.

## Running the notebook
1. Activate the project virtual environment and ensure the `.env` file sits alongside the notebook folder (the shared template populates expected variables).
2. Launch JupyterLab or VS Code, open `embedding-ingest-patterns.ipynb`, and execute cells sequentially. Every cell emits contextual print statements to narrate progress.
3. If the auto-embedding section fails with `VecDBError`, adjust `EMBED_MODEL_NAME` in `.env` to a model provisioned on your VecDB instance or skip that section.
4. After the cleanup cell completes, the schema returns to its original state ready for another pass or adjacent demos.
