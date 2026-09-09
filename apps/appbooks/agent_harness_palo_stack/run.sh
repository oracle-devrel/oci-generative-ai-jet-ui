#!/usr/bin/env bash
# Launch the Total Recall appbook.
#   • Uses your active environment (a Python venv or conda). If neither is active
#     but a `total_recall` conda env exists, it activates that.
#   • Ensures FastAPI/uvicorn/sse-starlette are present, then runs uvicorn.
set -euo pipefail
cd "$(dirname "$0")"

# Respect an already-active virtual environment; otherwise fall back to the conda env if present.
if [ -z "${VIRTUAL_ENV:-}" ] && command -v conda >/dev/null 2>&1 && conda env list 2>/dev/null | grep -q '/total_recall$\|total_recall '; then
  # shellcheck disable=SC1091
  source "$(conda info --base)/etc/profile.d/conda.sh"
  conda activate total_recall
fi

python -c "import fastapi, sse_starlette" 2>/dev/null || pip install -q "fastapi>=0.110" "uvicorn>=0.27" "sse-starlette>=2.0"

HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8000}"
echo "→ Total Recall appbook on http://${HOST}:${PORT}"
exec uvicorn backend.main:app --host "${HOST}" --port "${PORT}" "$@"
