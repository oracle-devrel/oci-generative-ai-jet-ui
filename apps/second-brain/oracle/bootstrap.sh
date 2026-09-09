#!/usr/bin/env bash
# Post-boot setup for the local Oracle 26ai container: apply schema, grant model rights,
# load the ONNX embedding model. Idempotent — safe to re-run. Requires the container
# (ccc-oracle) started via docker-compose, and oracle/models/all_MiniLM_L12_v2.onnx present
# (run ./download-model.sh first).
set -euo pipefail
cd "$(dirname "$0")"

# read ONLY the two passwords from .env — sourcing the whole file executes it as shell,
# which breaks on any unquoted value with a space (and runs more than a bootstrap should)
env_val() { grep -m1 "^$1=" .env 2>/dev/null | cut -d= -f2-; }
ORA="$(env_val ORACLE_PWD)"; ORA="${ORA:-${ORACLE_PWD:-CHANGE_ME_SysPwd1}}"
APP="$(env_val APP_PWD)";    APP="${APP:-${APP_PWD:-CHANGE_ME_AppPwd1}}"
DSN="localhost:1521/FREEPDB1"

echo "waiting for Oracle to be healthy..."
until [ "$(docker inspect -f '{{.State.Health.Status}}' ccc-oracle 2>/dev/null || echo none)" = "healthy" ]; do
  sleep 5; printf '.'
done
echo " ready."

echo "applying schema (as CCC)..."
docker exec -i ccc-oracle bash -lc "sqlplus -s CCC/${APP}@${DSN}" <<'SQL'
whenever sqlerror continue
-- idempotent reset: drop only what exists, so a FRESH database stays silent
-- (a wall of ORA-00942 here used to scare first-time readers; nothing was wrong)
begin
  for v in (select view_name from user_views
            where view_name in ('POST_DV','TOOL_STATS','WIKI_PAGE_DV')) loop
    execute immediate 'drop view ' || v.view_name;
  end loop;
  for t in (select table_name from user_tables
            where table_name in ('CONTENT_CHUNKS','MEDIA','POSTS','DEALS','BRANDS',
                                 'PLATFORMS','AGENT_MEMORY','SEMANTIC_MEMORY',
                                 'CONVERSATIONS','PROCEDURAL_MEMORY','WIKI_META',
                                 'PAGE_LINKS','PAGE_SOURCES','WIKI_PAGES','ANALYTICS')) loop
    execute immediate 'drop table ' || t.table_name || ' cascade constraints';
  end loop;
end;
/
@/container-entrypoint-initdb.d/01_content_duality.sql
@/container-entrypoint-initdb.d/02_agent_memory.sql
@/container-entrypoint-initdb.d/03_semantic_memory.sql
@/container-entrypoint-initdb.d/04_content_chunks.sql
@/container-entrypoint-initdb.d/05_conversational_memory.sql
@/container-entrypoint-initdb.d/06_procedural_memory.sql
@/container-entrypoint-initdb.d/07_wiki.sql
@/container-entrypoint-initdb.d/08_analytics.sql
exit
SQL

echo "granting model rights + directory (as SYSTEM)..."
docker exec -i ccc-oracle bash -lc "sqlplus -s system/${ORA}@${DSN}" <<'SQL'
create or replace directory VEC_MODELS as '/models';
grant read on directory VEC_MODELS to CCC;
grant create mining model to CCC;
exit
SQL

echo "loading ONNX embedding model 'MINILM' (as CCC)..."
docker exec -i ccc-oracle bash -lc "sqlplus -s CCC/${APP}@${DSN}" <<'SQL'
set serveroutput on
begin
  begin dbms_vector.drop_onnx_model('MINILM'); exception when others then null; end;
  dbms_vector.load_onnx_model('VEC_MODELS','all_MiniLM_L12_v2.onnx','MINILM',
    json('{"function":"embedding","embeddingOutput":"embedding","input":{"input":["DATA"]}}'));
  dbms_output.put_line('MINILM loaded.');
end;
/
exit
SQL

echo "bootstrap complete."
