#!/usr/bin/env bash
# Launch the Agent Memory Checklist appbook on http://127.0.0.1:8890 (PORT overrides).
set -euo pipefail
cd "$(dirname "$0")"
python -c "import fastapi, uvicorn, oracledb, anthropic, numpy" 2>/dev/null || pip install -q -r requirements.txt
exec python server.py --port "${PORT:-8890}"
