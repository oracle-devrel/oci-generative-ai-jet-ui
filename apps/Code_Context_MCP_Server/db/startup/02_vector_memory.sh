#!/bin/bash
# Every start: make sure the vector memory pool exists, so in-memory HNSW indexes can be built.
# It cannot be raised on a running instance (ORA-51950), so the first time it is written to the
# spfile and the instance restarts once. Later starts find it set and do nothing.
set -euo pipefail
current=$(sqlplus -s / as sysdba <<'SQL'
set heading off feedback off pagesize 0
select nvl(max(value), '0') from v$spparameter where name = 'vector_memory_size';
exit
SQL
)
current=$(echo "$current" | tr -d '[:space:]')
if [ "$current" != "0" ]; then
  echo "vector memory pool already set ($current)"
  exit 0
fi
sqlplus -s / as sysdba <<'SQL'
whenever sqlerror exit failure
set feedback off
alter system set vector_memory_size = 256M scope = spfile;
alter pluggable database freepdb1 save state;
shutdown immediate
startup
exit
SQL
echo "vector memory pool set to 256M; instance restarted"
