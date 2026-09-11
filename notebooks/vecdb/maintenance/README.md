[![Jupyter](https://img.shields.io/badge/Jupyter-Notebook-F37626?logo=jupyter&logoColor=white)](#) [![Python 3.10+](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)](#) [![oracle-vecdb](https://img.shields.io/badge/oracle-vecdb-F80000?logo=oracle&logoColor=white)](#)

# Maintenance & Indexing Notebook

`maintenance-indexing.ipynb` highlights lifecycle actions for VecDB tables: deletion, reindexing, archival, and cleanup.

## Highlights
- Describe tables to inspect vector counts and metadata.
- Delete vectors by ID (e.g., retention policies) and request reindexing.
- Copy remaining rows into an archive table before dropping the original.

## Prerequisites
- `.env` with VecDB credentials.
- Python 3.10+ with `oracle-vecdb`, `python-dotenv`, `pandas`.

Execute the notebook to sample maintenance routines and drop the demo tables when done.
