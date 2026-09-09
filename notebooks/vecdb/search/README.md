[![Jupyter](https://img.shields.io/badge/Jupyter-Notebook-F37626?logo=jupyter&logoColor=white)](#) [![Python 3.10+](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)](#) [![oracle-vecdb](https://img.shields.io/badge/oracle-vecdb-F80000?logo=oracle&logoColor=white)](#)

# Advanced Search & Diagnostics Notebook

`search-diagnostics.ipynb` walks through advanced semantic search tooling in Oracle VecDB with inline messaging that clarifies each step during execution.

## What this notebook demonstrates
- Load connection details from `.env`, build an `OracleVecDB` client, and echo resolved configuration values.
- Create an annotated search table, seed deterministic embeddings, and preview the marketing-style metadata payload.
- Run vector queries with range filters (`$gte`) to target high-priority content.
- Demonstrate logical filters using `$or` to mix channel and audience criteria.
- Compare range, equality, `AND`, and `OR` filter shapes in a compact filter playground summary.
- Enable `debug_flags` (when supported) and surface the diagnostic payload returned from VecDB.
- Trigger a controlled error by querying a missing table and catch it cleanly with `VecDBError` plus a generic fallback.
- Drop the demo table at the end to keep the environment tidy for repeated runs.

## Prerequisites
- `.env` with `VECDB_REST_URL`, `VECDB_USERNAME`/`VECDB_USER`, `VECDB_PASSWORD`, and optional `SEARCH_TABLE` override.
- Python 3.10+ with `oracle-vecdb`, `python-dotenv`, `pandas` (installed automatically by the notebook if missing).
- Network access to your VecDB endpoint.

## Running the notebook
1. Activate the project virtual environment and open `search-diagnostics.ipynb` in Jupyter or VS Code.
2. Execute cells sequentially; each section prints contextual status updates to describe the operation being run.
3. If `debug_flags` are not available in your deployment, the response may omit profiling data; that cell will still show the returned payload for inspection.
4. Use the cleanup cell to remove the demo table when finished so subsequent runs start clean.
