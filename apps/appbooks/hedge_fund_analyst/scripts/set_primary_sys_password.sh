#!/bin/bash
# True Cache provisioning logs in to the primary as SYS over the network, so SYS needs a known password.
# Generates one, sets it on the primary, verifies a remote login, then stores it in .env (mode 600). Never printed.
set -euo pipefail
cd "$(dirname "$0")/.."
CONTAINER=$(sed -n 's/^HF_DB_CONTAINER=//p' .env)
PW="Tc$(openssl rand -hex 14)"
printf "set echo off feedback on\nalter user sys identified by \"%s\" container=all;\nexit\n" "$PW" \
  | docker exec -i "$CONTAINER" sqlplus -s / as sysdba 2>&1 | grep -o -E 'ORA-[0-9]+|User altered' | sort -u
if docker exec -e PW="$PW" "$CONTAINER" bash -c 'echo "select database_role from v\$database;" | sqlplus -s "sys/${PW}@//localhost:1521/FREE as sysdba"' | grep -q PRIMARY; then
  grep -v '^HF_PRIMARY_SYS_PASSWORD=' .env > .env.tmp || true
  echo "HF_PRIMARY_SYS_PASSWORD=$PW" >> .env.tmp && mv .env.tmp .env && chmod 600 .env
  echo "SYS login verified over the network; password stored in .env as HF_PRIMARY_SYS_PASSWORD."
else
  echo "SYS login failed; .env not changed." >&2; exit 1
fi
