#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
python3 scripts/local_env.py
# Reuse an explicitly configured primary. Standalone mode provisions only the demo primary.
if ! docker inspect "$(sed -n 's/^HF_DB_CONTAINER=//p' .env)" >/dev/null 2>&1; then
  docker compose up -d --wait database
fi
./setup.sh
exec ./run.sh
