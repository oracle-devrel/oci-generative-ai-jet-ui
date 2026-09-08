#!/bin/bash

set -euo pipefail

CONTAINER_NAME="oracle-generative-ui-data-chat"
ORACLE_PWD="${ORACLE_ADMIN_PWD:-OraclePwd_2026}"
APP_USER="${ORACLE_USER:-DATA_CHAT}"
APP_PASSWORD="${ORACLE_PASSWORD:-DataChatPwd_2026}"

echo "=== Generative UI Data Chat: Oracle 26ai setup ==="

if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
  if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo "Container ${CONTAINER_NAME} is already running."
  else
    echo "Starting existing container ${CONTAINER_NAME}..."
    docker start "${CONTAINER_NAME}"
  fi
else
  echo "Creating Oracle Database Free container..."
  docker compose up -d
fi

echo "Waiting for FREEPDB1 to accept SQL connections..."
ready=0
for _ in $(seq 1 120); do
  if docker exec "${CONTAINER_NAME}" bash -lc "sqlplus -s / as sysdba <<'SQL'
WHENEVER SQLERROR EXIT SQL.SQLCODE
SET HEADING OFF FEEDBACK OFF PAGESIZE 0
ALTER SESSION SET CONTAINER=FREEPDB1;
SELECT 1 FROM DUAL;
SQL" >/dev/null 2>&1; then
    echo "Oracle FREEPDB1 is ready."
    ready=1
    break
  fi
  printf "."
  sleep 5
done
echo

if [ "${ready}" -ne 1 ]; then
  echo "Oracle FREEPDB1 did not become ready in time. Check logs with: docker logs ${CONTAINER_NAME}" >&2
  exit 1
fi

echo "Creating application user ${APP_USER} if needed..."
docker exec "${CONTAINER_NAME}" bash -lc "sqlplus -s / as sysdba <<SQL
WHENEVER SQLERROR EXIT SQL.SQLCODE
ALTER SESSION SET CONTAINER=FREEPDB1;

DECLARE
  user_count NUMBER;
BEGIN
  SELECT COUNT(*) INTO user_count FROM dba_users WHERE username = UPPER('${APP_USER}');
  IF user_count = 0 THEN
    EXECUTE IMMEDIATE 'CREATE USER ${APP_USER} IDENTIFIED BY \"${APP_PASSWORD}\"';
  END IF;
END;
/

GRANT CONNECT, RESOURCE TO ${APP_USER};
GRANT UNLIMITED TABLESPACE TO ${APP_USER};
GRANT EXECUTE ON CTXSYS.CTX_DDL TO ${APP_USER};
SQL"

echo "Local connection string: 127.0.0.1:1522/FREEPDB1"
echo "Run: npm run db:seed"
