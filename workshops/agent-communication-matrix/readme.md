# Agent Communication Matrix — Vector Search Demo

This repository demonstrates an end-to-end local demo of embedding-based vector search using:

- an Oracle Database with vector support (VECTOR column + HNSW index)
- Ollama for local embeddings and LLMs
- a small Python notebook suite that exercises embedding, indexing, and search

The demo is intentionally minimal and reproducible so others can clone and run the notebooks locally.

## Intent

The goal of this demo is to provide a compact, self-contained example that shows:

- generating embeddings for short text chunks with a local embedding model
- storing vectors in Oracle's `VECTOR` column and creating a vector index
- performing nearest-neighbour search using `VECTOR_DISTANCE` / `TO_VECTOR`
- measuring embedding and search latency across sample queries

This is suitable for learning, experimentation, and benchmarking on a local machine or CI environment.

## Requirements

- Docker & Docker Compose (for Oracle DB and Ollama)
- Python 3.10+ (3.14 tested in this repo)
- Sufficient memory for Oracle + Ollama containers (recommend 8GB+ available)
- Optional: Oracle Instant Client if your Python `oracledb` connection uses thick mode

Files of interest:

- `notebooks/` — interactive demo notebooks (setup, embedding pipeline, vector search, benchmarks)
- `scripts/init-db.sh` — creates DB user, tables and vector index
- `scripts/load_corpus.py` — loads `data/chunks.txt` into `kb_chunks` with embeddings
- `scripts/pull-models.sh` — pulls required Ollama models
- `scripts/run_demo.sh` — one-step demo runner (convenience)

## Quickstart

1. Clone the repo:

```bash
git clone https://github.com/your-org/agent-communication-matrix.git
cd agent-communication-matrix
```

2. Prepare environment variables. The repo expects a `.env` file at the project root with keys similar to:

```text
DB_USER=agentuser
DB_PASS=AgentPass_123
DB_DSN=localhost:1521/FREEPDB1
OLLAMA_URL=http://localhost:11434
EMBED_MODEL=nomic-embed-text
```

You can copy the existing `.env` or set environment variables in your shell.

3. Run the demo helper (recommended):

```bash
bash scripts/run_demo.sh
```

This will:

- start Docker services (via `docker compose up -d`)
- pull required Ollama models
- initialize the Oracle schema and vector index
- create a Python virtualenv and install requirements
- load the sample corpus into `kb_chunks`
- launch Jupyter Lab so you can run the notebooks interactively

4. If you prefer to run steps manually, follow these core commands:

```bash
# Start services
docker compose up -d

# Pull Ollama models
bash scripts/pull-models.sh

# Initialize DB schema and index
bash scripts/init-db.sh

# Create venv (first-time only) and install deps
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt

# Load sample corpus (in venv)
.venv/bin/python scripts/load_corpus.py

# Start Jupyter Lab
.venv/bin/jupyter lab --no-browser --ip=0.0.0.0
```

Then open the notebooks in `notebooks/` and run cells in order:

1. `01-setup-and-data-loading.ipynb` — verify DB and preview rows
2. `02-embedding-pipeline.ipynb` — measure embedding latency
3. `03-vector-search-demo.ipynb` — run the vector search demo (now uses bind variables/CLOBs and reads LOBs)
4. `04-pattern-comparison.ipynb` and `05-benchmarks-visualization.ipynb` — optional analysis

## Notes & Portability

- The repository's Oracle image provides `VECTOR`, `VECTOR_DISTANCE` and `TO_VECTOR` used in the demo. If using a different Oracle build, confirm vector functions and index support.
- The embedding model must produce vectors with the same dimensionality as the database `VECTOR` column (the demo uses 768-dim embeddings).
- `python-oracledb` can operate in thin mode (no Instant Client) — consult its docs if you encounter connection issues.
- If you change `EMBED_MODEL`, update `.env` and ensure Ollama has the model.

## Security & Licensing

This demo contains no secrets in the repository. Always avoid committing production credentials. When publishing, ensure your `.env` and any credentials are excluded (see `.gitignore`).

## Run the app

From agent-communication-matrix:

1. Start the stack:
   - `docker compose up -d`

2. Wait until Oracle is ready:
   - `docker compose logs -f oracle-db`
   - Look for `DATABASE IS READY TO USE!`

3. Initialize the database schema and sample data:
   - init-db.sh

4. Pull Ollama models if needed:
   - pull-models.sh

## Optional demo API

If you want the Pattern 3 API service:

- `docker compose --profile demo up -d`

## Notes

- If you don’t already have a .env file, copy the example:
  - `cp .env.example .env`
