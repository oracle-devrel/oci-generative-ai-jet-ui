#!/usr/bin/env bash
set -euo pipefail

# ============================================================
# picooraclaw — One-Command Installer
# PicoOraClaw is a fork of PicoClaw that adds Oracle AI Database as a backend for persistent storage
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/jasperan/picooraclaw/main/install.sh | bash
#
# Override install location:
#   PROJECT_DIR=/opt/myapp curl -fsSL ... | bash
# ============================================================

REPO_URL="https://github.com/jasperan/picooraclaw.git"
PROJECT="picooraclaw"
BRANCH="main"
INSTALL_DIR="${PROJECT_DIR:-$(pwd)/$PROJECT}"

# ── Colors ──────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

info()    { echo -e "${BLUE}→${NC} $1"; }
success() { echo -e "${GREEN}✓${NC} $1"; }
warn()    { echo -e "${YELLOW}!${NC} $1"; }
fail()    { echo -e "${RED}✗ $1${NC}"; exit 1; }
command_exists() { command -v "$1" &>/dev/null; }

print_banner() {
    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BOLD}  picooraclaw${NC}"
    echo -e "  PicoOraClaw is a fork of PicoClaw that adds Oracle AI Database as a backend for persistent storage"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
}

clone_repo() {
    if [ -d "$INSTALL_DIR" ]; then
        warn "Directory $INSTALL_DIR already exists"
        info "Pulling latest changes..."
        (cd "$INSTALL_DIR" && git pull origin "$BRANCH" 2>/dev/null) || true
    else
        info "Cloning repository..."
        git clone --depth 1 -b "$BRANCH" "$REPO_URL" "$INSTALL_DIR" || fail "Clone failed. Check your internet connection."
    fi
    success "Repository ready at $INSTALL_DIR"
}

check_prereqs() {
    info "Checking prerequisites..."
    command_exists git || fail "Git is required — https://git-scm.com/"
    success "Git $(git --version | cut -d' ' -f3)"

    command_exists go || fail "Go 1.21+ is required — https://go.dev/dl/"
    success "Go $(go version | cut -d' ' -f3)"
}

install_deps() {
    cd "$INSTALL_DIR"
    info "Downloading Go modules..."
    go mod download
    success "Modules downloaded"

    info "Building binary..."
    go build -o "${INSTALL_DIR}/picooraclaw" ./... 2>/dev/null || go build -o "${INSTALL_DIR}/picooraclaw" . 2>/dev/null || {
        warn "Auto-build failed — check README for specific build instructions"
        return
    }
    success "Binary built: ${INSTALL_DIR}/picooraclaw"

    # Optionally install to PATH
    LOCAL_BIN="${HOME}/.local/bin"
    mkdir -p "$LOCAL_BIN"
    cp "${INSTALL_DIR}/picooraclaw" "$LOCAL_BIN/" 2>/dev/null && \
        success "Installed to $LOCAL_BIN/picooraclaw" || true
}

main() {
    print_banner
    check_prereqs
    clone_repo
    install_deps
    print_done
}

print_done() {
    echo ""
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "  ${BOLD}Installation complete!${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "  ${BOLD}Location:${NC}  $INSTALL_DIR"
    echo -e "  ${BOLD}Binary:${NC}   $INSTALL_DIR/picooraclaw"
    echo -e "  ${BOLD}Run:${NC}      picooraclaw --help"
    echo ""
}

main "$@"
