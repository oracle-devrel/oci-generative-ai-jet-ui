#!/usr/bin/env bash
# 01_start_oracle.sh — Start the Oracle AI Database Free container for the soccer workshop.
# Usage: bash 01_start_oracle.sh [--force-recreate]
# Engine:  auto-detects Docker (preferred) or Podman; either works.
# Arch:    on arm64 Macs uses gvenzl/oracle-free (ARM-native);
#          on amd64/x86_64 uses the official container-registry.oracle.com image.
# Waits up to 7.5 minutes for the container to become healthy.
# The DSN, PDB (FREEPDB1), and admin password are identical across both images,
# so .env / ORACLE_DSN never change.
set -euo pipefail

cd "$(dirname "$0")/../../../.."

# --- 1. Detect the container engine -----------------------------------------
ENGINE=""
COMPOSE=""
if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
  ENGINE="docker"
  if docker compose version >/dev/null 2>&1; then
    COMPOSE="docker compose"
  elif command -v docker-compose >/dev/null 2>&1; then
    COMPOSE="docker-compose"
  fi
elif command -v podman >/dev/null 2>&1; then
  ENGINE="podman"
  if podman compose version >/dev/null 2>&1; then
    COMPOSE="podman compose"
  elif command -v podman-compose >/dev/null 2>&1; then
    COMPOSE="podman-compose"
  fi
fi

if [ -z "$ENGINE" ]; then
  echo "ERROR: no working container engine found." >&2
  echo "Install Docker (https://docs.docker.com/get-docker/) or Podman" >&2
  echo "(https://podman.io/), then re-run. On Docker, make sure the daemon is running." >&2
  exit 1
fi
if [ -z "$COMPOSE" ]; then
  echo "ERROR: found '$ENGINE' but no compose command." >&2
  echo "Install the compose plugin: 'docker compose' / 'podman compose' / 'podman-compose'." >&2
  exit 1
fi
echo "Container engine: $ENGINE (compose: $COMPOSE)"

# --- 2. Pick an image for this OS / arch ------------------------------------
OS="$(uname -s)"
ARCH="$(uname -m)"
if [ "$OS" = "Darwin" ] && { [ "$ARCH" = "arm64" ] || [ "$ARCH" = "aarch64" ]; }; then
  # Apple Silicon: the official image is amd64-only; use the ARM-native image.
  export ORACLE_IMAGE="gvenzl/oracle-free:latest"
  echo "Apple Silicon detected -> using ARM-native image: $ORACLE_IMAGE"
else
  # Default: official amd64 image (compose default applies if ORACLE_IMAGE unset).
  echo "Using default image: container-registry.oracle.com/database/free:latest"
fi

# --- 3. Admin password compatibility across images --------------------------
# Official image reads ORACLE_PWD; gvenzl/oracle-free reads ORACLE_PASSWORD.
# Export both (same value) so whichever image we picked starts with the
# workshop's well-known SYSTEM password.
ADMIN_PWD="${ORACLE_ADMIN_PASSWORD:-SoccerAdmin2026#}"
export ORACLE_ADMIN_PASSWORD="$ADMIN_PWD"
export ORACLE_PASSWORD="$ADMIN_PWD"

# --- 4. Start and wait for health -------------------------------------------
$COMPOSE -f docker/docker-compose.yml up -d

echo "Waiting for Oracle to become healthy..."
for _ in $(seq 1 90); do
  status=$($ENGINE inspect --format='{{.State.Health.Status}}' soccer-oracle 2>/dev/null || echo "starting")
  if [ "$status" = "healthy" ]; then
    echo "Oracle is healthy."
    exit 0
  fi
  sleep 5
done
echo "Oracle did not become healthy in time." >&2
exit 1
