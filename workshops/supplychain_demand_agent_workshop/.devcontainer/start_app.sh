#!/usr/bin/env bash
# postStartCommand hook. Starts the chat app every time the codespace
# resumes. Idempotent — re-runs cleanly if already running.
#
# NOTE: the chat app (`app/backend/`, `app/frontend/`) is delivered in a
# follow-up iteration. Until then this script is a no-op that prints the
# next-step pointer.
set -euo pipefail

WORKSHOP_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$WORKSHOP_ROOT"

LOG_DIR="$WORKSHOP_ROOT/.devcontainer/logs"
mkdir -p "$LOG_DIR"

# ── Backend: FastAPI on :8000 ─────────────────────────────────────────────
if [ -f "app/backend/main.py" ]; then
  if ! pgrep -f "uvicorn .*app.backend" > /dev/null; then
    echo "▶ Starting backend on :8000 …"
    setsid nohup python -m uvicorn app.backend.main:app \
      --host 0.0.0.0 --port 8000 \
      > "$LOG_DIR/backend.log" 2>&1 &
  else
    echo "✅ Backend already running."
  fi
else
  echo "ℹ  app/backend/main.py not present yet — backend will be wired in the next iteration."
fi

# ── Frontend: Vite on :3000 ───────────────────────────────────────────────
if [ -f "app/frontend/package.json" ]; then
  if ! pgrep -f "vite.*--port 3000" > /dev/null; then
    echo "▶ Starting frontend on :3000 …"
    (cd app/frontend && setsid nohup npm run dev -- --host 0.0.0.0 --port 3000 \
        > "$LOG_DIR/frontend.log" 2>&1 &)
  else
    echo "✅ Frontend already running."
  fi
else
  echo "ℹ  app/frontend/package.json not present yet — frontend will be wired in the next iteration."
fi

echo
echo "Next step: open workshop/notebook_student.ipynb"
