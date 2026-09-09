#!/bin/sh
# Unpack the Autonomous wallet from a Fly secret (base64 of a tar.gz), then start the server.
set -e
if [ -n "$BRAIN_WALLET_B64" ]; then
  mkdir -p /wallet
  echo "$BRAIN_WALLET_B64" | base64 -d | tar xz -C /wallet
  export DB_WALLET_DIR=/wallet
fi
exec uvicorn mcp_http:app --host 0.0.0.0 --port "${PORT:-8000}"
