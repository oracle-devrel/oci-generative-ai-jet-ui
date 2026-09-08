#!/usr/bin/env bash
set -euo pipefail

# Run the demo end-to-end locally.
# Steps: start containers, pull Ollama models, init DB, create venv, install deps, load corpus, launch Jupyter

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

echo "[demo] Starting Docker services..."
docker compose up -d

echo "[demo] Pulling Ollama models..."
bash scripts/pull-models.sh

echo "[demo] Initializing Oracle DB schema and index..."
bash scripts/init-db.sh

if [ ! -d ".venv" ]; then
  echo "[demo] Creating Python virtualenv (.venv)..."
  python3 -m venv .venv
fi

echo "[demo] Activating venv and installing requirements..."
# shellcheck source=/dev/null
. .venv/bin/activate
pip install -r requirements.txt

echo "[demo] Loading sample corpus into kb_chunks..."
.venv/bin/python scripts/load_corpus.py

echo "[demo] Launching Jupyter Lab (no-browser)."
echo "Open http://localhost:8888/ in your browser, or check the terminal output for the token."
.venv/bin/jupyter lab --no-browser --ip=0.0.0.0
