#!/bin/bash
set -e

echo "============================================"
echo "  Enterprise Data Agent Workshop — Build"
echo "============================================"

WORKSPACE="${WORKSPACE:-$(pwd)}"

echo ""
echo "[1/4] Installing workshop notebook dependencies..."
pip install -q --no-cache-dir -r "$WORKSPACE/requirements.txt"

echo ""
echo "[2/4] Installing app backend dependencies..."
pip install -q --no-cache-dir -r "$WORKSPACE/app/backend/requirements.txt"

echo ""
echo "[3/4] Registering Jupyter kernel..."
python -m ipykernel install --user --name python3 --display-name "Python 3.11"

echo ""
echo "[4/4] Installing app frontend dependencies (npm)..."
cd "$WORKSPACE/app/frontend"
npm install --no-audit --no-fund --silent
cd "$WORKSPACE"

echo ""
echo "Build complete."
echo "  • Workshop notebook deps installed."
echo "  • App backend (Python) deps installed."
echo "  • App frontend (npm) deps installed."
echo "  Oracle + bootstrap + seed run on first start (postCreateCommand)."
echo "============================================"
