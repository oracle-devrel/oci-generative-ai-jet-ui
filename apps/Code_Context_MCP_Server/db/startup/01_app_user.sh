#!/bin/bash
# Every start: make sure the application user exists in FREEPDB1 with the password from .env.
# The image ships a prebuilt database, so scripts/setup never runs; scripts/startup does.
# Reads DB_USER and DB_PASSWORD from the container environment; never echoes the password.
set -euo pipefail
sqlplus -s / as sysdba <<SQL
whenever sqlerror exit failure
set feedback off
alter session set container = FREEPDB1;
declare
  n number;
begin
  select count(*) into n from dba_users where username = upper('${DB_USER}');
  if n = 0 then
    execute immediate 'create user ${DB_USER} identified by "${DB_PASSWORD}" default tablespace users quota unlimited on users';
    execute immediate 'grant db_developer_role to ${DB_USER}';
  else
    execute immediate 'alter user ${DB_USER} identified by "${DB_PASSWORD}" account unlock';
  end if;
end;
/
exit
SQL
echo "application user ${DB_USER} ready in FREEPDB1"
