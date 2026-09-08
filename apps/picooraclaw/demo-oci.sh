#!/bin/bash
# PicoOraClaw OCI GenAI Demo Script
# ──────────────────────────────────
# Runs picooraclaw against OCI Generative AI using xAI Grok 4.20.
#
# Pre-reqs:
#   1. make build
#   2. pip install -r oci-genai/requirements.txt
#   3. ~/.oci/config with valid credentials
#   4. OCI_COMPARTMENT_ID env var set
#   5. (optional) OCI_REGION env var (default: us-chicago-1)
#
# Usage: ./demo-oci.sh                   (Grok 4, default)
#        ./demo-oci.sh xai.grok-3-mini   (Grok 3 Mini, fast + reasoning traces)
#        ./demo-oci.sh xai.grok-4.20     (Grok 4.20, if available in your region)

set -euo pipefail

PICO="./build/picooraclaw-linux-amd64"
MODEL="${1:-xai.grok-4}"
SESSION="demo-oci-$(date +%s)"
PAUSE=3
CONFIG="$HOME/.picooraclaw/config.json"
PROXY_PID=""

# ── Colors ───────────────────────────────────────────────────
CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
WHITE='\033[1;37m'
DIM='\033[2m'
BOLD='\033[1m'
NC='\033[0m'

# ── Helpers ──────────────────────────────────────────────────
beat() {
    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BOLD}${YELLOW}  $1${NC}"
    echo -e "${DIM}  $2${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    sleep 2
}

run_cmd() {
    echo -e "  ${GREEN}\$${NC} ${WHITE}$*${NC}"
    echo ""
    eval "$@"
    echo ""
    sleep "$PAUSE"
}

cleanup() {
    if [ -n "$PROXY_PID" ] && kill -0 "$PROXY_PID" 2>/dev/null; then
        echo -e "\n${DIM}Stopping OCI GenAI proxy (PID $PROXY_PID)...${NC}"
        kill "$PROXY_PID" 2>/dev/null || true
        wait "$PROXY_PID" 2>/dev/null || true
    fi
}
trap cleanup EXIT

# ── Preflight ────────────────────────────────────────────────
if [ ! -f "$PICO" ]; then
    echo "Binary not found at $PICO. Run 'make build' first."
    exit 1
fi

if [ ! -f "$HOME/.oci/config" ]; then
    echo "OCI config not found at ~/.oci/config"
    echo "See: https://docs.oracle.com/en-us/iaas/Content/API/Concepts/sdkconfig.htm"
    exit 1
fi

# Auto-read from ~/.oci/config DEFAULT profile if env vars aren't set
OCI_PROFILE="${OCI_PROFILE:-DEFAULT}"
if [ -z "${OCI_COMPARTMENT_ID:-}" ]; then
    # Use tenancy OCID as root compartment
    OCI_COMPARTMENT_ID=$(awk -v p="[$OCI_PROFILE]" '
        $0 == p {found=1; next}
        /^\[/ {found=0}
        found && /^tenancy=/ {sub(/^tenancy=/, ""); print; exit}
    ' "$HOME/.oci/config")
    if [ -z "$OCI_COMPARTMENT_ID" ]; then
        echo "Could not read tenancy from ~/.oci/config [$OCI_PROFILE]"
        exit 1
    fi
    export OCI_COMPARTMENT_ID
    echo -e "${DIM}Using tenancy as compartment: ${OCI_COMPARTMENT_ID:0:40}...${NC}"
fi
if [ -z "${OCI_REGION:-}" ]; then
    OCI_REGION=$(awk -v p="[$OCI_PROFILE]" '
        $0 == p {found=1; next}
        /^\[/ {found=0}
        found && /^region=/ {sub(/^region=/, ""); print; exit}
    ' "$HOME/.oci/config")
    export OCI_REGION="${OCI_REGION:-us-chicago-1}"
    echo -e "${DIM}Using region: ${OCI_REGION}${NC}"
fi

if ! python3 -c "import oci_openai" 2>/dev/null; then
    echo "oci-openai not installed. Run: pip install -r oci-genai/requirements.txt"
    exit 1
fi

# ── Start OCI GenAI Proxy ───────────────────────────────────
# Kill any stale proxy on the port
kill $(lsof -ti:9999) 2>/dev/null || true

echo -e "${DIM}Starting OCI GenAI proxy...${NC}"
python3 oci-genai/proxy.py &
PROXY_PID=$!
sleep 2

# Verify proxy is running
if ! kill -0 "$PROXY_PID" 2>/dev/null; then
    echo "OCI GenAI proxy failed to start."
    exit 1
fi

# Wait for proxy to be ready
for i in $(seq 1 10); do
    if curl -s http://localhost:9999/v1/health >/dev/null 2>&1; then
        echo -e "${GREEN}Proxy ready at localhost:9999${NC}"
        break
    fi
    sleep 1
done

# ── Configure PicoOraClaw for OCI GenAI ─────────────────────
# Back up current config and swap to OCI
cp "$CONFIG" "${CONFIG}.bak" 2>/dev/null || true
cat > "$CONFIG" << OCICONF
{
  "agents": {
    "defaults": {
      "workspace": "~/.picooraclaw/workspace",
      "restrict_to_workspace": true,
      "provider": "openai",
      "model": "$MODEL",
      "max_tokens": 8192,
      "temperature": 0.7,
      "max_tool_iterations": 20
    }
  },
  "providers": {
    "openai": {
      "api_key": "oci-genai",
      "api_base": "http://localhost:9999/v1"
    }
  },
  "oracle": {
    "enabled": false
  },
  "heartbeat": {
    "enabled": false
  },
  "gateway": {
    "host": "0.0.0.0",
    "port": 18790
  }
}
OCICONF

# Ensure skills are installed
$PICO skills install-builtin >/dev/null 2>&1 || true

# Seed a demo file for the filesystem beat
mkdir -p ~/.picooraclaw/workspace
cat > ~/.picooraclaw/workspace/demo.txt << 'DEMOFILE'
import oracledb

conn = oracledb.connect(user="picooraclaw", password="secret", dsn="localhost:1521/FREEPDB1")
cursor = conn.cursor()
cursor.execute("SELECT * FROM PICO_MEMORIES WHERE VECTOR_DISTANCE(embedding, :query_vec) < 0.3")
for row in cursor:
    print(row)
conn.close()
DEMOFILE

# ── Title Card ───────────────────────────────────────────────
clear
echo ""
echo -e "${BOLD}${WHITE}"
cat << 'TITLE'

    ██████╗ ██╗ ██████╗ ██████╗  ██████╗ ██████╗  █████╗  ██████╗██╗      █████╗ ██╗    ██╗
    ██╔══██╗██║██╔════╝██╔═══██╗██╔═══██╗██╔══██╗██╔══██╗██╔════╝██║     ██╔══██╗██║    ██║
    ██████╔╝██║██║     ██║   ██║██║   ██║██████╔╝███████║██║     ██║     ███████║██║ █╗ ██║
    ██╔═══╝ ██║██║     ██║   ██║██║   ██║██╔══██╗██╔══██║██║     ██║     ██╔══██║██║███╗██║
    ██║     ██║╚██████╗╚██████╔╝╚██████╔╝██║  ██║██║  ██║╚██████╗███████╗██║  ██║╚███╔███╔╝
    ╚═╝     ╚═╝ ╚═════╝ ╚═════╝  ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝╚══════╝╚═╝  ╚═╝ ╚══╝╚══╝

TITLE
echo -e "${NC}"
echo -e "  ${DIM}Ultra-lightweight AI assistant  |  Single binary  |  ~10MB RAM${NC}"
echo -e "  ${DIM}Powered by ${MODEL} via OCI Generative AI + Oracle AI Database${NC}"
echo ""
sleep 4

# ═════════════════════════════════════════════════════════════
# BEAT 1: One-shot query — show CLI + LLM working
# ═════════════════════════════════════════════════════════════
beat "1/5  One-Shot Query" \
     "Single command, cloud inference via OCI Generative AI."

run_cmd "$PICO agent --stream -m 'Introduce yourself in two sentences. What are you and what can you do?' -s $SESSION"

# ═════════════════════════════════════════════════════════════
# BEAT 2: Filesystem tools — agent reads files
# ═════════════════════════════════════════════════════════════
beat "2/5  Filesystem Tools" \
     "The agent can read and reason about files in its workspace."

run_cmd "$PICO agent --stream -m 'Read the file demo.txt and explain what the code does' -s $SESSION"

# ═════════════════════════════════════════════════════════════
# BEAT 3: Remember + Recall — persistent semantic memory
# ═════════════════════════════════════════════════════════════
beat "3/5  Semantic Memory" \
     "Store facts, recall them later with natural language. Backed by Oracle AI Vector Search."

run_cmd "$PICO agent --stream -m 'Remember this: my favorite language is Go and I deploy all my workloads on Oracle Cloud Infrastructure using Ampere A1 instances' -s $SESSION"

run_cmd "$PICO agent --stream -m 'What cloud platform and compute shape do I prefer?' -s $SESSION"

# ═════════════════════════════════════════════════════════════
# BEAT 4: Shell execution — run system commands
# ═════════════════════════════════════════════════════════════
beat "4/5  Shell Execution" \
     "The agent can run commands and reason about the output."

run_cmd "$PICO agent --stream -m 'Run uname -a, then run df -h, and give me a quick summary of this system' -s $SESSION"

# ═════════════════════════════════════════════════════════════
# BEAT 5: Skills ecosystem
# ═════════════════════════════════════════════════════════════
beat "5/5  Skills Ecosystem" \
     "Extensible skill system: install from GitHub, write your own, or use builtins."

run_cmd "$PICO skills list"

# ── Outro ────────────────────────────────────────────────────
echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BOLD}${WHITE}  Demo complete.${NC}"
echo ""
echo -e "  ${DIM}Single Go binary. Cross-compiles to Linux, macOS, Windows.${NC}"
echo -e "  ${DIM}Runs on RISC-V, ARM64, x86_64. Fits on a \$5 board.${NC}"
echo -e "  ${DIM}Cloud inference via OCI Generative AI (${MODEL}).${NC}"
echo -e "  ${DIM}Oracle AI Database for production memory + vector search.${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Restore original config
if [ -f "${CONFIG}.bak" ]; then
    mv "${CONFIG}.bak" "$CONFIG"
    echo -e "${DIM}Config restored.${NC}"
fi
