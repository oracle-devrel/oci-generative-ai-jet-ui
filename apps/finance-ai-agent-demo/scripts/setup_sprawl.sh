#!/usr/bin/env bash
# ============================================================
# Sprawl Architecture Database Setup
# Provisions four separate databases for the finance AI agent:
#   - PostgreSQL 16 + PostGIS  (relational / spatial)
#   - Neo4j                    (graph)
#   - MongoDB                  (document / JSON)
#   - Qdrant                   (vector search)
# ============================================================
set -e

COMPOSE_FILE="docker-compose.sprawl.yml"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# ------------------------------------------------------------
# Helper: wait for a container's health check to pass
# Usage: wait_for <container_name> <friendly_name> <max_seconds>
# ------------------------------------------------------------
wait_for() {
  local container="$1"
  local name="$2"
  local max_wait="${3:-120}"
  local elapsed=0

  printf "  Waiting for %s to become healthy..." "$name"
  while [ "$elapsed" -lt "$max_wait" ]; do
    status=$(docker inspect --format='{{.State.Health.Status}}' "$container" 2>/dev/null || echo "starting")
    if [ "$status" = "healthy" ]; then
      printf " ready (%ds)\n" "$elapsed"
      return 0
    fi
    sleep 2
    elapsed=$((elapsed + 2))
  done

  printf " TIMEOUT after %ds\n" "$max_wait"
  echo "ERROR: $name did not become healthy in time." >&2
  exit 1
}

# ============================================================
echo "=== Sprawl Architecture Database Setup ==="
echo ""

# 1. Start all containers
echo "[1/4] Starting containers..."
cd "$PROJECT_DIR"
docker-compose -f "$COMPOSE_FILE" up -d

echo ""
echo "[2/4] Waiting for databases to be ready..."

# 2. Wait for each service to pass its health check
wait_for "sprawl-postgres" "PostgreSQL"   120
wait_for "sprawl-neo4j"    "Neo4j"        120
wait_for "sprawl-mongodb"  "MongoDB"      120
wait_for "sprawl-qdrant"   "Qdrant"        60

# 3. Install PostgreSQL extensions (pgvector is pre-installed; add PostGIS)
echo ""
echo "[3/4] Installing PostgreSQL extensions..."

# Install PostGIS packages inside the pgvector container
echo "  Installing PostGIS packages (this may take a moment)..."
docker exec sprawl-postgres bash -c \
  "apt-get update -qq && apt-get install -y -qq postgresql-16-postgis-3 > /dev/null 2>&1"

docker exec sprawl-postgres \
  psql -U vector -d financedb -c "CREATE EXTENSION IF NOT EXISTS vector;"
echo "  pgvector extension ready."

docker exec sprawl-postgres \
  psql -U vector -d financedb -c "CREATE EXTENSION IF NOT EXISTS postgis;"
echo "  PostGIS extension ready."

# 4. Print connection details
echo ""
echo "[4/4] Connection details"
echo "============================================================"
echo ""
echo "  PostgreSQL (relational + spatial)"
echo "    Host:     localhost:5432"
echo "    User:     vector"
echo "    Password: VectorPwd_2025"
echo "    Database: financedb"
echo "    DSN:      postgresql://vector:VectorPwd_2025@localhost:5432/financedb"
echo ""
echo "  Neo4j (graph)"
echo "    Browser:  http://localhost:7474"
echo "    Bolt:     bolt://localhost:7687"
echo "    User:     neo4j"
echo "    Password: Neo4jPwd_2025"
echo ""
echo "  MongoDB (document / JSON)"
echo "    URI:      mongodb://root:MongoPwd_2025@localhost:27017"
echo "    Port:     27017"
echo "    User:     root"
echo "    Password: MongoPwd_2025"
echo ""
echo "  Qdrant (vector search)"
echo "    HTTP API: http://localhost:6333"
echo "    gRPC:     localhost:6334"
echo "    Dashboard: http://localhost:6333/dashboard"
echo ""
echo "============================================================"
echo "=== Sprawl architecture is ready ==="
