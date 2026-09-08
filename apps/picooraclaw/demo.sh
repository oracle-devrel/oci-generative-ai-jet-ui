#!/bin/bash
# PicoOraClaw 1-Minute Demo Script
# ─────────────────────────────────
# Pre-reqs:
#   1. make build
#   2. picooraclaw onboard  (if first run)
#   3. ollama running with gemma4 loaded
#   4. (optional) docker compose --profile oracle up -d oracle-db
#
# Usage: ./demo.sh              (runs with gemma4:26b MoE, reliable tool calling)
#        ./demo.sh gemma4:e4b   (runs with e4b, faster but weaker at tools)
# Tip: pre-warm the model first:  ./build/picooraclaw-linux-amd64 agent -m "hi"

set -euo pipefail

PICO="./build/picooraclaw-linux-amd64"
MODEL="${1:-gemma4:26b}"
SESSION="demo-$(date +%s)"
PAUSE=3
CONFIG="$HOME/.picooraclaw/config.json"

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

# ── Preflight ────────────────────────────────────────────────
if [ ! -f "$PICO" ]; then
    echo "Binary not found at $PICO. Run 'make build' first."
    exit 1
fi

if ! ollama show "$MODEL" >/dev/null 2>&1; then
    echo "$MODEL not found in ollama. Run 'ollama pull $MODEL' first."
    exit 1
fi

# Set the model in config
if [ -f "$CONFIG" ]; then
    sed -i "s|\"model\":.*|\"model\": \"$MODEL\",|" "$CONFIG"
fi

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

# Pre-warm: load model into memory so first demo response is fast
echo -e "${DIM}Pre-warming ${MODEL}...${NC}"
$PICO agent --stream -m "hi" -s warmup >/dev/null 2>&1 || true

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
echo -e "  ${DIM}Powered by ${MODEL} + Oracle AI Database${NC}"
echo ""
sleep 4

# ═════════════════════════════════════════════════════════════
# BEAT 1: One-shot query — show CLI + LLM working
# ═════════════════════════════════════════════════════════════
beat "1/5  One-Shot Query" \
     "Single command, instant answer. No setup, no servers."

run_cmd "$PICO agent --stream -m 'Introduce yourself in two sentences. What are you and what can you do?' -s $SESSION"

# ═════════════════════════════════════════════════════════════
# BEAT 2: Filesystem tools — agent reads and writes files
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
echo -e "  ${DIM}Runs on RISC-V, ARM64, x86_64. Fits on a $5 board.${NC}"
echo -e "  ${DIM}Oracle AI Database for production memory + vector search.${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
