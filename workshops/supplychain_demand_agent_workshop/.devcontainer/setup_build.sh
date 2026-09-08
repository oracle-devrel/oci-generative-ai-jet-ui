#!/usr/bin/env bash
# One-time build-time setup. Runs as `onCreateCommand`.
# Installs Python + Node deps. Does NOT touch Oracle.
set -euo pipefail

WORKSHOP_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$WORKSHOP_ROOT"

echo "▶ Installing workshop Python dependencies …"
pip install --quiet --upgrade pip
pip install --quiet \
    langchain \
    langgraph \
    langgraph-supervisor \
    langgraph-oracledb \
    langchain-oracledb \
    langchain-openai \
    datasets \
    jupyter \
    nbconvert

echo "▶ Installing app backend Python dependencies …"
if [ -f "app/backend/requirements.txt" ]; then
  pip install --quiet -r app/backend/requirements.txt
fi

echo "▶ Installing app frontend Node dependencies …"
if [ -f "app/frontend/package.json" ]; then
  (cd app/frontend && npm install --silent)
fi

echo "✅ Build-time setup complete."
