#!/bin/bash
set -e

echo "============================================"
echo "  From RAG to Agents Workshop - Build"
echo "============================================"

echo ""
echo "[1/2] Installing Python dependencies..."
pip install -q --no-cache-dir \
  oracledb \
  pandas \
  sentence-transformers \
  datasets \
  einops \
  "numpy<2.0" \
  openai \
  openai-agents \
  tqdm \
  jupyter \
  ipykernel \
  ipywidgets \
  matplotlib \
  nest_asyncio

echo ""
echo "[2/2] Registering Jupyter kernel..."
python -m ipykernel install --user --name python3 --display-name "From RAG to Agents Workshop"

echo ""
echo "Build complete. Oracle will start when the Codespace opens."
echo "============================================"
