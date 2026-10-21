#!/bin/bash
# Provision the workshop's Oracle AI Database — idempotent, safe on every start.
#
# Called from TWO places:
#   postCreateCommand  (first build)      — bash .devcontainer/provision.sh
#   postStartCommand   (every open)       — start_app.sh calls it before the app
#
# Everything here is safe to re-run: a Codespace whose database volume was
# recreated, whose container was stopped, or whose seed died half-way heals
# itself on the next open, and a fully provisioned database costs a handful of
# SELECTs. Nothing in FINANCE is dropped unless the seed layer is actually
# missing, so a student's live session is never wiped by a restart.
#
# Manual re-run:  bash .devcontainer/provision.sh
# Probe only:     bash .devcontainer/provision.sh --probe-only

set +e
set -u
set -o pipefail   # `cmd | tee | tail` must report cmd's failure, not tail's

WORKSPACE="${WORKSPACE:-$(pwd)}"
LOG_DIR="$WORKSPACE/.devcontainer/logs"
PROBE_ONLY=0
[ "${1:-}" = "--probe-only" ] && PROBE_ONLY=1
mkdir -p "$LOG_DIR"

# The devcontainer python (deps installed by setup_build.sh on create). Override
# with PYTHON=... when running against another interpreter.
PY="${PYTHON:-python3}"

echo "============================================"
echo "  Financial Fraud Agent Harness Workshop — Oracle provisioning"
echo "  (idempotent: only what is missing gets built)"
echo "============================================"

# The chat loop needs an OCI key; everything else works without one.
if [ -z "${OCI_GENAI_API_KEY:-}" ] && ! grep -q "^OCI_GENAI_API_KEY=..*" "$WORKSPACE/app/.env" 2>/dev/null; then
  echo ""
  echo "  ⚠️  No OCI GenAI key (OCI_GENAI_API_KEY) in the environment or app/.env."
  echo "      Setup continues; the chat loop needs the key. To add it later:"
  echo "        echo 'OCI_GENAI_API_KEY=...' >> $WORKSPACE/app/.env"
  echo "        bash .devcontainer/start_app.sh"
fi

if [ $PROBE_ONLY -eq 0 ]; then
  # --- 1. Docker daemon -----------------------------------------------------
  echo ""
  echo "[1/5] Waiting for the Docker daemon..."
  for i in $(seq 1 15); do
    docker info > /dev/null 2>&1 && echo "  Docker is ready." && break \
      || { [ $i -lt 15 ] && echo "  waiting… ($i/15)" && sleep 3; }
  done

  # --- 2. Oracle container --------------------------------------------------
  echo ""
  echo "[2/5] Starting Oracle AI Database (3–5 minutes on first run)..."

  # A volume created by the *slim* image (no Spatial, no Text) cannot be reused
  # with the full image — Spatial indexes and Oracle Text both abort. Start fresh.
  EXISTING_IMAGE=$(docker inspect oracle-free --format '{{.Config.Image}}' 2>/dev/null || true)
  if [ -n "$EXISTING_IMAGE" ] && echo "$EXISTING_IMAGE" | grep -q 'slim'; then
    echo "  ⚠ existing oracle-free runs the slim image ($EXISTING_IMAGE) — recreating on the full image"
    docker rm -f oracle-free > /dev/null 2>&1 || true
    for volume in financial-fraud-agent-harness-workshop_oracle-data \
                financial-fraud-agent-harness-workshop-lightweight_oracle-data \
                devcontainer_oracle-data; do
      docker volume rm "$volume" > /dev/null 2>&1 || true
    done
  fi

  if ! docker ps --format '{{.Names}}' | grep -q '^oracle-free$'; then
    if docker ps -a --format '{{.Names}}' | grep -q '^oracle-free$'; then
      echo "  container exists but is stopped — starting it"
      docker start oracle-free > /dev/null 2>&1
    else
      if docker compose -f "$WORKSPACE/.devcontainer/docker-compose.yml" up -d oracle > /dev/null 2>&1; then
        echo "  container created"
      else
        echo "  ERROR: docker compose up failed — run: docker compose -f .devcontainer/docker-compose.yml up oracle"
      fi
    fi
  else
    echo "  container already running"
  fi

  # --- 3. Wait for the listener --------------------------------------------
  echo ""
  echo "[3/5] Waiting for Oracle to accept connections..."
  ORACLE_UP=0
  for i in $(seq 1 40); do
    if docker exec oracle-free healthcheck.sh > /dev/null 2>&1; then
      echo "  Oracle is accepting connections."
      ORACLE_UP=1
      break
    fi
    echo "  attempt $i/40 — waiting 8s..."
    sleep 8
  done
  if [ $ORACLE_UP -eq 0 ]; then
    echo "  ERROR: Oracle did not start. Run: docker logs oracle-free"
    exit 1
  fi

  # A volume carried over from an earlier workshop may hold different passwords;
  # normalise SYS to the workshop default before anything tries to log in.
  docker exec oracle-free resetPassword OraclePwd_2025 > /dev/null 2>&1 || true
fi

# --- 4. app/.env ------------------------------------------------------------
# The app and the provisioning scripts read app/.env; the lifecycle shell also
# receives OCI/Oracle config as Codespaces secrets. Materialise both, so a
# rotated secret reaches the app on the next start (lifecycle shells do not
# reliably inherit the interactive environment).
if [ $PROBE_ONLY -eq 0 ]; then
echo ""
echo "[4/5] Materializing app/.env..."
if [ ! -f "$WORKSPACE/app/.env" ]; then
  cp "$WORKSPACE/app/.env.example" "$WORKSPACE/app/.env"
fi

"$PY" - <<'PYEOF'
import os, pathlib

env_path = pathlib.Path(os.environ.get("WORKSPACE", os.getcwd())) / "app" / ".env"
text = env_path.read_text()


def set_kv(text, key, value):
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if line.lstrip().startswith(f"{key}="):
            lines[i] = f"{key}={value}"
            break
    else:
        lines.append(f"{key}={value}")
    return "\n".join(lines) + "\n"


# OCI-only workshop: pin the provider, keep the OpenAI fallback blank so an OCI
# failure is a visible error rather than a silent switch to another account.
text = set_kv(text, "LLM_PROVIDER", "oci")
text = set_kv(text, "LLM_MODEL", "xai.grok-4.3")
text = set_kv(text, "OPENAI_API_KEY", "")
text = set_kv(text, "LLM_FALLBACK_MODEL", "")

# Primary (Phoenix) keys 1-6, Chicago fallback endpoint/keys 1-6, optional backup model and cooldown.
secret_keys = ["OCI_GENAI_API_KEY", "OCI_GENAI_ENDPOINT", "TAVILY_API_KEY", "OCI_GENAI_FALLBACK_ENDPOINT",
               "OCI_GENAI_FALLBACK_API_KEY", "OCI_GENAI_BACKUP_MODEL", "OCI_GENAI_FALLBACK_COOLDOWN_S"]
secret_keys += [f"OCI_GENAI_API_KEY_{i}" for i in range(2, 7)]
secret_keys += [f"OCI_GENAI_FALLBACK_API_KEY_{i}" for i in range(2, 7)]
for key in secret_keys:
    if os.environ.get(key):
        text = set_kv(text, key, os.environ[key])

env_path.write_text(text)
print(f"  patched {env_path} with the available secrets")
PYEOF
fi

# --- 5. Layer probe: run only what is missing ------------------------------
echo ""
echo "[5/5] Checking what the database already has..."

PROBE="$(WORKSPACE="$WORKSPACE" "$PY" - <<'PYEOF'
"""Report which provisioning layer is missing, as BOOTSTRAP/SEED/ADVANCED/IDENTITY lines."""
import os, pathlib, sys

env_path = pathlib.Path(os.environ["WORKSPACE"]) / "app" / ".env"
for line in (env_path.read_text().splitlines() if env_path.exists() else []):
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        key, value = line.split("=", 1)
        os.environ.setdefault(key, value)

import oracledb  # noqa: E402  (after the env is loaded)

dsn = os.environ.get("ORACLE_DSN", "localhost:1521/FREEPDB1")
user = os.environ.get("ORACLE_AGENT_USER", "AGENT")
pwd = os.environ.get("ORACLE_AGENT_PASS", "AgentPwd_2025")
embed = os.environ.get("ONNX_EMBED_MODEL", "ALL_MINILM_L12_V2")

state = {"BOOTSTRAP": "missing", "SEED": "missing", "ADVANCED": "missing", "IDENTITY": "missing"}
try:
    conn = oracledb.connect(user=user, password=pwd, dsn=dsn)
    cur = conn.cursor()

    def scalar(sql, default=0):
        try:
            cur.execute(sql)
            return cur.fetchone()[0]
        except oracledb.DatabaseError:
            return default

    # L1 — bootstrap: the harness's own schema (login works, embedder, registries, DBFS).
    models = scalar(f"SELECT COUNT(*) FROM user_mining_models WHERE model_name = '{embed}'")
    registries = scalar("SELECT COUNT(*) FROM user_tables WHERE table_name IN ('TOOLBOX', 'SKILLBOX')")
    dbfs = scalar("SELECT COUNT(*) FROM dba_tablespaces WHERE tablespace_name = 'AGENT_DBFS_TS'")
    if models and registries == 2 and dbfs:
        state["BOOTSTRAP"] = "ok"

    # L2 — seed: the bank. Tables + duality views + rows + an ingested skillbox.
    tables = scalar("SELECT COUNT(*) FROM all_tables WHERE owner = 'FINANCE'")
    views = scalar("SELECT COUNT(*) FROM all_views WHERE owner = 'FINANCE' "
                   "AND view_name IN ('ACCOUNT_DV', 'CUSTOMER_DV')")
    txns = scalar("SELECT COUNT(*) FROM finance.transactions")
    skills = scalar("SELECT COUNT(*) FROM agent.skillbox")
    if tables >= 15 and views == 2 and txns >= 1000 and skills > 0:
        state["SEED"] = "ok"

    # L3 — advanced: Oracle Text index for the hybrid retrieval leg.
    if scalar("SELECT COUNT(*) FROM user_indexes WHERE index_name = 'EDA_MEMORY_TEXT_IDX'"):
        state["ADVANCED"] = "ok"

    # L4 — identity: the kernel-side policy set (installed by setup_deep_security.py).
    if scalar("SELECT COUNT(*) FROM all_policies WHERE object_owner = 'FINANCE'") >= 10:
        state["IDENTITY"] = "ok"

    conn.close()
except Exception as exc:  # login refused, instance not ready — everything is "missing"
    print(f"  probe could not read the database: {str(exc).splitlines()[0]}", file=sys.stderr)

for key, value in state.items():
    print(f"{key}={value}")
PYEOF
)"

echo "$PROBE" | sed 's/^/  /'

if [ $PROBE_ONLY -eq 1 ]; then
  echo ""
  echo "  --probe-only: nothing was changed."
  exit 0
fi

need() { grep -q "^$1=ok" <<<"$PROBE" && return 1 || return 0; }

if need BOOTSTRAP; then
  echo ""
  echo "▸ AGENT schema / ONNX embedder / registries missing — running scripts/bootstrap.py"
  if ! ( cd "$WORKSPACE/app" && "$PY" scripts/bootstrap.py ) 2>&1 | tee -a "$LOG_DIR/bootstrap.log" | tail -20
  then
    echo "  ⚠ bootstrap.py did not finish — see $LOG_DIR/bootstrap.log, then re-run this script"
  fi
fi

if need SEED; then
  echo ""
  echo "▸ FINANCE / duality views / skillbox missing or incomplete — running scripts/seed.py"
  if ! ( cd "$WORKSPACE/app" && "$PY" scripts/seed.py ) 2>&1 | tee -a "$LOG_DIR/seed.log" | tail -25
  then
    echo "  ⚠ seed.py did not finish — see $LOG_DIR/seed.log, then re-run this script"
  fi
fi

if need ADVANCED; then
  echo ""
  echo "▸ Oracle Text index missing — running scripts/setup_advanced.py"
  if ! ( cd "$WORKSPACE/app" && "$PY" scripts/setup_advanced.py ) 2>&1 | tee -a "$LOG_DIR/setup_advanced.log" | tail -20
  then
    echo "  ⚠ setup_advanced.py did not finish — see $LOG_DIR/setup_advanced.log"
  fi
fi

if need IDENTITY; then
  echo ""
  echo "▸ Identity rules missing — running scripts/setup_deep_security.py"
  if ! ( cd "$WORKSPACE/app" && "$PY" scripts/setup_deep_security.py ) 2>&1 | tee -a "$LOG_DIR/setup_deep_security.log" | tail -20
  then
    echo "  ⚠ setup_deep_security.py did not finish — see $LOG_DIR/setup_deep_security.log"
  fi
fi

if ! need BOOTSTRAP && ! need SEED && ! need ADVANCED && ! need IDENTITY; then
  echo ""
  echo "  Nothing to do — the database is fully provisioned."
fi

echo ""
echo "============================================"
echo "  Oracle ready."
echo "    • Notebook:  notebook_student.ipynb   (answer key: notebook_complete.ipynb)"
echo "    • App:       http://localhost:3000    (backend: :8000)"
echo "    • Logs:      $LOG_DIR/"
echo "  Re-run by hand:  bash .devcontainer/provision.sh"
echo "============================================"
