#!/bin/bash
# The primary runs in ARCHIVELOG mode (required for True Cache) and writes ~200 MB per log switch
# into the container volume. Without backups those logs only fill the disk, which halts the database.
# Keep two hours (enough for True Cache gap resolution) and delete older ones every 20 minutes.
set -uo pipefail
cd "$(dirname "$0")/.."
CONTAINER=$(sed -n 's/^HF_DB_CONTAINER=//p' .env)
while true; do
  docker exec "$CONTAINER" bash -c "rman target / <<'EOF' >/dev/null 2>&1
DELETE NOPROMPT ARCHIVELOG ALL COMPLETED BEFORE 'SYSDATE-2/24';
EXIT
EOF"
  echo "$(date -Iseconds) archive housekeeping done; volume $(docker exec "$CONTAINER" df -h /opt/oracle/oradata | awk 'NR==2{print $5}') used"
  [ "${1:-}" = "--once" ] && break
  sleep 1200
done
