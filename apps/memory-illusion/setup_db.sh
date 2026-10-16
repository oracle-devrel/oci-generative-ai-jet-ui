#!/usr/bin/env bash
# Idempotent setup: start the oracle26ai container (reused from the RAG course)
# and bootstrap the `memdemo` user for the Agent Memory demos.
set -euo pipefail

CONTAINER=oracle26ai
DB_PASS=Welcome_123
DEMO_USER=memdemo

if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER}$"; then
  echo "▶ starting container ${CONTAINER}…"
  docker start "${CONTAINER}" >/dev/null
fi

echo "▶ waiting for the database to accept connections…"
for i in $(seq 1 60); do
  if docker exec -i "${CONTAINER}" bash -lc \
    "echo 'SELECT 1 FROM DUAL;' | sqlplus -S -L sys/${DB_PASS}@localhost:1521/FREEPDB1 as sysdba" \
    2>/dev/null | grep -q '^-\+$'; then
    echo "  ✓ database is up"
    break
  fi
  [ "$i" = 60 ] && { echo "  ✗ database did not come up in time"; exit 1; }
  sleep 5
done

echo "▶ ensuring user ${DEMO_USER} exists…"
docker exec -i "${CONTAINER}" sqlplus -S -L "sys/${DB_PASS}@localhost:1521/FREEPDB1" as sysdba <<SQL
WHENEVER SQLERROR CONTINUE
DECLARE n NUMBER;
BEGIN
  SELECT COUNT(*) INTO n FROM dba_users WHERE username = UPPER('${DEMO_USER}');
  IF n = 0 THEN
    EXECUTE IMMEDIATE 'CREATE USER ${DEMO_USER} IDENTIFIED BY ${DB_PASS}
      DEFAULT TABLESPACE users QUOTA UNLIMITED ON users';
  END IF;
END;
/
GRANT CREATE SESSION, CREATE TABLE, CREATE SEQUENCE, CREATE VIEW, CREATE JOB, CREATE PROCEDURE TO ${DEMO_USER};
EXIT;
SQL
echo "  ✓ ${DEMO_USER}/${DB_PASS} ready on ${CONTAINER} (localhost:1521/FREEPDB1)"
