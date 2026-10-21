#!/bin/bash
# postStartCommand — runs every time the Codespace starts.
# Provisions Oracle (idempotent, see provision.sh), then launches backend +
# frontend in the background.
#
# Tolerant of partial failures: each step prints clear status, and the script
# does NOT `set -e` so one bad step won't leave the user with neither service.

set +e
set -u

echo "============================================"
echo "  Financial Fraud Agent Harness Workshop — App Auto-Start"
echo "============================================"

WORKSPACE="${WORKSPACE:-$(pwd)}"
LOG_DIR="$WORKSPACE/.devcontainer/logs"
mkdir -p "$LOG_DIR"

# -----------------------------------------------------------------------------
# 1. Oracle + provisioning — idempotent, so every Codespace open ends fully
#    provisioned even if the database volume was recreated, the container was
#    stopped, or a previous seed died half-way. A warm database costs a handful
#    of SELECTs (see .devcontainer/provision.sh).
# -----------------------------------------------------------------------------
echo ""
echo "[1/3] Provisioning Oracle (idempotent — only what is missing gets built)..."
if ! bash "$WORKSPACE/.devcontainer/provision.sh"; then
  echo "  ERROR: Oracle never came up. Run:  docker logs oracle-free"
  exit 1
fi
ORACLE_OK=1

# -----------------------------------------------------------------------------
# 3. Backend
# -----------------------------------------------------------------------------
echo ""
echo "[2/3] Starting agent backend on :8000 (logs → $LOG_DIR/backend.log)..."

# Match how we launch it below (`python -u app.py`); the old pattern
# "python app.py" never matched, so a restart collided on :8000.
pkill -f "python -u app.py" 2>/dev/null
sleep 1

# setsid puts the backend in its own session so it survives this script
# exiting (postStartCommand returns, parent shell goes away). Without it,
# Codespaces occasionally SIGHUPs the process group on script exit, which
# leaves the forwarded port returning 502 even though the build appeared
# to succeed in the logs.
cd "$WORKSPACE/app/backend"
setsid nohup python -u app.py > "$LOG_DIR/backend.log" 2>&1 < /dev/null &
BACKEND_PID=$!
disown $BACKEND_PID 2>/dev/null || true
cd "$WORKSPACE"
echo "  backend PID: $BACKEND_PID"

# Wait up to 120s for /api/health to respond
BACKEND_OK=0
for i in $(seq 1 120); do
  if curl -sf http://localhost:8000/api/health > /dev/null 2>&1; then
    echo "  backend ready (${i}s)."
    BACKEND_OK=1
    break
  fi
  # If the process died early, surface it fast.
  if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
    echo "  ERROR: backend process exited. Last 40 lines:"
    tail -40 "$LOG_DIR/backend.log" | sed 's/^/    /'
    break
  fi
  sleep 1
done

if [ $BACKEND_OK -eq 0 ] && kill -0 "$BACKEND_PID" 2>/dev/null; then
  echo "  WARNING: backend hasn't answered /api/health within 120s. Tail of log:"
  tail -20 "$LOG_DIR/backend.log" | sed 's/^/    /'
  echo "  (Continuing — the backend may still come up. Frontend will start regardless.)"
fi

# -----------------------------------------------------------------------------
# 4. Frontend
# -----------------------------------------------------------------------------
echo ""
echo "[3/3] Starting agent UI on :3000 (logs → $LOG_DIR/frontend.log)..."

# node_modules may not exist on a fresh container.
if [ ! -d "$WORKSPACE/app/frontend/node_modules" ]; then
  echo "  node_modules missing — running 'npm install'..."
  cd "$WORKSPACE/app/frontend"
  npm install --no-audit --no-fund --silent 2>&1 | tee -a "$LOG_DIR/npm-install.log"
  cd "$WORKSPACE"
fi

pkill -f "$WORKSPACE/app/frontend/node_modules/vite/bin/vite.js" 2>/dev/null
sleep 1

# Run vite directly (not through `npm run dev`) so we don't have an extra npm
# wrapper that can disappear on SIGHUP and orphan the real server. setsid +
# nohup + disown together make sure the dev server keeps running after this
# postStartCommand returns — without all three, Codespaces sometimes serves
# 502 on the forwarded :3000 URL because vite was reaped on script exit.
cd "$WORKSPACE/app/frontend"
VITE_BIN="$WORKSPACE/app/frontend/node_modules/vite/bin/vite.js"
setsid nohup node "$VITE_BIN" --host 0.0.0.0 --port 3000 --clearScreen false \
  > "$LOG_DIR/frontend.log" 2>&1 < /dev/null &
FRONTEND_PID=$!
disown $FRONTEND_PID 2>/dev/null || true
cd "$WORKSPACE"
echo "  frontend PID: $FRONTEND_PID"

# Wait up to 60s for Vite to bind to :3000
FRONTEND_OK=0
for i in $(seq 1 60); do
  if curl -sf http://localhost:3000 > /dev/null 2>&1; then
    echo "  frontend ready (${i}s)."
    FRONTEND_OK=1
    break
  fi
  if ! kill -0 "$FRONTEND_PID" 2>/dev/null; then
    echo "  ERROR: frontend process exited. Last 40 lines:"
    tail -40 "$LOG_DIR/frontend.log" | sed 's/^/    /'
    break
  fi
  sleep 1
done

if [ $FRONTEND_OK -eq 0 ] && kill -0 "$FRONTEND_PID" 2>/dev/null; then
  echo "  WARNING: frontend didn't bind to :3000 within 60s. Tail of log:"
  tail -20 "$LOG_DIR/frontend.log" | sed 's/^/    /'
fi

# Belt-and-suspenders: verify the frontend is still listening 5s after the
# initial ready check. Vite's first HTTP response can succeed before its
# module graph is built; if dependency resolution then errors out, the
# process exits and the codespace proxy returns 502 to the next request.
# This catches that case and dumps the log instead of silently leaving the
# user with a dead UI.
if [ $FRONTEND_OK -eq 1 ]; then
  sleep 5
  if ! kill -0 "$FRONTEND_PID" 2>/dev/null || ! curl -sf http://localhost:3000 > /dev/null 2>&1; then
    echo "  ERROR: frontend reported ready but is no longer responsive. Tail of log:"
    tail -40 "$LOG_DIR/frontend.log" | sed 's/^/    /'
    FRONTEND_OK=0
  fi
fi

# -----------------------------------------------------------------------------
# Summary
# -----------------------------------------------------------------------------
# If we're inside Codespaces, surface the public URL for the UI as well. The
# preview should auto-open via onAutoForward, but printing a clickable URL
# here gives the user a fallback if the preview was dismissed or didn't
# trigger on this particular VS Code build.
PUBLIC_UI_URL=""
if [ -n "${CODESPACE_NAME:-}" ]; then
  DOMAIN="${GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN:-app.github.dev}"
  PUBLIC_UI_URL="https://${CODESPACE_NAME}-3000.${DOMAIN}"
fi

echo ""
echo "============================================"
echo "  Status:"
echo "    Oracle:   $([ $ORACLE_OK   -eq 1 ] && echo OK || echo FAIL)"
echo "    Backend:  $([ $BACKEND_OK  -eq 1 ] && echo OK || echo 'NOT READY (check log)')"
echo "    Frontend: $([ $FRONTEND_OK -eq 1 ] && echo OK || echo 'NOT READY (check log)')"
echo ""
echo "  • Frontend (UI):   http://localhost:3000   (auto-forwarded by Codespaces)"
if [ -n "$PUBLIC_UI_URL" ]; then
  echo "    Public URL:      $PUBLIC_UI_URL"
fi
echo "  • Backend (API):   http://localhost:8000"
echo "  • Notebook:        notebook_student.ipynb"
echo ""
echo "  Logs:              $LOG_DIR/{backend,frontend,npm-install,bootstrap,seed,setup_advanced,setup_deep_security}.log"
echo "  Restart manually:  bash .devcontainer/start_app.sh"
echo "============================================"
