---
title: Common Oracle errors in local LangChain.js apps
source: oracle-errors
category: troubleshooting
product: Oracle Database
priority: high
audience: developer
tags: ora-28001, ora-01017, connection, podman
---

# Common Oracle errors in local LangChain.js apps

Most local connection failures are caused by using credentials for one container while connecting to another service, or by an expired schema password.

## ORA-28001

`ORA-28001: The account has expired. The password must be changed.` means the username is recognized, but the database requires a password reset. Reset the schema password in the target PDB, then rerun `pnpm db:check`.

## ORA-01017

`ORA-01017: invalid credential or not authorized; logon denied` usually means the user, password, port, or service name do not belong together. Check whether you are connecting to the right container and service, for example `localhost:1522/FREEPDB1` versus `localhost:1521/FREEPDB1`.

## SP2-0157

`SP2-0157` from SQL Plus means the SQL Plus client could not connect after retries. Validate the service name, listener port, and whether the database container is fully started.

## Environment variables

The sample accepts `ORACLE_USER`, `ORACLE_PASSWORD`, `ORACLE_CONNECT_STRING`, and `ORACLE_DSN`. It also accepts `DB_USER`, `DB_PASSWORD`, `DB_CONNECT_STRING`, `DB_DSN`, and `ORACLEDB_CONNECTION_STRING` aliases for local conventions.
