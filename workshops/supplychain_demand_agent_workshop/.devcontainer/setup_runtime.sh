#!/usr/bin/env bash
# Post-create lifecycle hook. Brings up Oracle, then runs the three
# pre-build steps the workshop notebook depends on:
#   1. bootstrap.py     — AGENT user + vector memory pool
#   2. onnx_setup.py    — download + load ALL_MINILM_L12_V2 ONNX model
#   3. seed_supplychain — HF dataset → OracleVS + AsyncOracleStore
#
# Idempotent. Safe to re-run.
#
# IMPORTANT: we deliberately do NOT use `set -e`. A failure in the ONNX
# download (URL rotated) or the HF seed (network blip) should not abort the
# whole post-create — `start_app.sh` (postStartCommand) still needs to run
# so the chat app can at least come up. Each step prints its own status so
# failures stay visible; the learner can re-run individual scripts from the
# terminal:
#
#     python app/scripts/onnx_setup.py
#     python app/scripts/seed_supplychain.py
set +e
set -u

WORKSHOP_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$WORKSHOP_ROOT"

LOG_DIR="$WORKSHOP_ROOT/.devcontainer/logs"
mkdir -p "$LOG_DIR"

# Track step outcomes so we can summarise at the end.
ORACLE_OK=0
BOOTSTRAP_OK=0
ONNX_OK=0
SEED_OK=0

# ── 1. Bring up Oracle Free ───────────────────────────────────────────────
echo ""
echo "[1/4] Starting Oracle Free container …"
docker compose -f .devcontainer/docker-compose.yml up -d

echo "      Waiting for Oracle to become healthy (3-5 min on first boot) …"
STATUS="starting"
for ATTEMPTS in $(seq 1 80); do
  STATUS=$(docker inspect -f '{{.State.Health.Status}}' oracle-free 2>/dev/null || echo "starting")
  if [ "$STATUS" = "healthy" ]; then
    echo "      ✅ Oracle is healthy."
    ORACLE_OK=1
    break
  fi
  sleep 15
  echo "      … still waiting ($STATUS, attempt $ATTEMPTS/80)"
done

if [ "$ORACLE_OK" -eq 0 ]; then
  echo "      ❌ Oracle never became healthy. Check 'docker logs oracle-free'." >&2
  echo "         Skipping bootstrap / onnx / seed; start_app.sh will still run."
fi

# ── 2. Bootstrap (AGENT user + vector pool) ───────────────────────────────
if [ "$ORACLE_OK" -eq 1 ]; then
  echo ""
  echo "[2/4] Running bootstrap.py …"
  if python app/scripts/bootstrap.py 2>&1 | tee "$LOG_DIR/bootstrap.log"; then
    BOOTSTRAP_OK=1

    # bootstrap may have set vector_memory_size in SPFILE; bounce so it takes effect.
    if grep -q "scope=spfile" "$LOG_DIR/bootstrap.log"; then
      echo "      Restarting Oracle so vector_memory_size takes effect …"
      docker compose -f .devcontainer/docker-compose.yml restart oracle-free
      sleep 30
      for _ in $(seq 1 40); do
        if [ "$(docker inspect -f '{{.State.Health.Status}}' oracle-free)" = "healthy" ]; then
          break
        fi
        sleep 10
      done
    fi
  else
    echo "      ❌ bootstrap failed — see $LOG_DIR/bootstrap.log"
  fi
fi

# ── 3. Load the ONNX embedder model ───────────────────────────────────────
if [ "$BOOTSTRAP_OK" -eq 1 ]; then
  echo ""
  echo "[3/4] Running onnx_setup.py …"
  if python app/scripts/onnx_setup.py 2>&1 | tee "$LOG_DIR/onnx_setup.log"; then
    ONNX_OK=1
  else
    echo "      ❌ onnx_setup failed — see $LOG_DIR/onnx_setup.log"
    echo "         The notebook can be opened, but in-DB embedding cells will fail."
    echo "         Re-run later with: python app/scripts/onnx_setup.py"
  fi
fi

# ── 4. Seed Hugging Face data → OracleVS + AsyncOracleStore ───────────────
if [ "$ONNX_OK" -eq 1 ]; then
  echo ""
  echo "[4/4] Running seed_supplychain.py …"
  if python app/scripts/seed_supplychain.py 2>&1 | tee "$LOG_DIR/seed.log"; then
    SEED_OK=1
  else
    echo "      ❌ seed failed — see $LOG_DIR/seed.log"
    echo "         Re-run later with: python app/scripts/seed_supplychain.py"
  fi
fi

# ── Summary ──────────────────────────────────────────────────────────────
echo ""
echo "============================================"
echo "  Runtime setup summary"
echo "============================================"
echo "  Oracle Free:        $([ $ORACLE_OK    -eq 1 ] && echo OK || echo FAIL)"
echo "  AGENT bootstrap:    $([ $BOOTSTRAP_OK -eq 1 ] && echo OK || echo FAIL)"
echo "  ONNX model load:    $([ $ONNX_OK      -eq 1 ] && echo OK || echo FAIL)"
echo "  HF data seed:       $([ $SEED_OK      -eq 1 ] && echo OK || echo FAIL)"
echo ""
echo "  Logs: $LOG_DIR/{bootstrap,onnx_setup,seed}.log"
echo "  Notebook: workshop/notebook_student.ipynb"
echo "  App will start on http://localhost:3000 once start_app.sh runs."
echo "============================================"
