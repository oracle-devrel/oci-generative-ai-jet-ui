[![Jupyter](https://img.shields.io-badge/Jupyter-Notebook-F37626?logo=jupyter&logoColor=white)](#) [![Python 3.10+](https://img.shields.io-badge/Python-3.10+-3776AB?logo=python&logoColor=white)](#) [![oracle-vecdb](https://img.shields.io-badge/oracle-vecdb-F80000?logo=oracle&logoColor=white)](#)

# Index-Model Workbench & HNSW Tuning Notebooks

This directory contains two complementary VecDB walkthroughs:

- `index-model-workbench.ipynb`: a guided tour of index lifecycle management, model catalog exploration, and annotation governance. Every section shares the same authenticated `OracleVecDB` client, making it easy to replay in any environment that provides the standard `.env` variables.
- `hnsw-efsearch-demo.ipynb`: a focused demo that creates an explicit HNSW index, monitors its job logs, and contrasts search requests using different `efsearch` (candidate beam) values. It also documents how to flip between deterministic demo vectors and hosted `SentenceTransformer` embeddings without editing code.

## Highlights
- Bootstrap a dedicated demo table, inspect baseline metadata, and provision an explicit HNSW index while reviewing index job rosters and logs (`index-model-workbench`).
- Enumerate available embedding models and surface rich metadata via `describe_model`, noting how the API behaves when hosted models are unavailable (`index-model-workbench`).
- Toggle between deterministic and hosted embeddings, submit HNSW index builds, and run paired queries that highlight how `efsearch` acts as the “number of candidates” knob (`hnsw-efsearch-demo`).
- Update table annotations with ownership metadata to mirror real-world governance practices, plus conclude with cleanup routines so both notebooks can be rerun without manual resets.

## Prerequisites
- `.env` with `VECDB_REST_URL`, `VECDB_USERNAME`, `VECDB_PASSWORD`, optional `INDEX_MODEL_TABLE` override.
- Python 3.10+ with `oracle-vecdb`, `python-dotenv`, `pandas`; `sentence-transformers` is optional but recommended for the HNSW demo when you want real embeddings.

Execute the notebooks top-to-bottom. The shared connection cells load credentials once, and the final cleanup steps leave VecDB tidy for future demos.
