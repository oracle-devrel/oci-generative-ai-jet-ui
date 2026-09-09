#!/usr/bin/env bash
# scripts/init-db.sh
# Creates the agentuser schema and the kb_chunks + agent_memory tables
# shared across Patterns 1, 2, and 3.

set -euo pipefail

source .env

docker exec -i oracle-db sqlplus -L "system/${ORACLE_PWD}@//localhost:1521/FREEPDB1" <<SQL
-- Create the application user
CREATE USER ${DB_USER} IDENTIFIED BY "${DB_PASS}";
GRANT CONNECT, RESOURCE, CREATE VIEW TO ${DB_USER};
ALTER USER ${DB_USER} QUOTA UNLIMITED ON USERS;
EXIT;
SQL

docker exec -i oracle-db sqlplus -L "${DB_USER}/${DB_PASS}@//localhost:1521/FREEPDB1" <<SQL
-- Pattern 1 + Pattern 3 shared: vector-indexed knowledge chunks
CREATE TABLE kb_chunks (
  id          NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  doc_id      VARCHAR2(128) NOT NULL,
  chunk_text  CLOB NOT NULL,
  embedding   VECTOR(768, FLOAT32),
  created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE VECTOR INDEX kb_chunks_vec_idx ON kb_chunks (embedding)
  ORGANIZATION INMEMORY NEIGHBOR GRAPH
  DISTANCE COSINE
  WITH TARGET ACCURACY 95;

-- Pattern 2: agent task memory with payload-by-reference
CREATE TABLE agent_memory (
  id            VARCHAR2(64) PRIMARY KEY,
  task_id       VARCHAR2(64) NOT NULL,
  from_agent    VARCHAR2(64),
  to_agent      VARCHAR2(64),
  findings      CLOB,
  source_refs   CLOB,
  draft         CLOB,
  embedding     VECTOR(768, FLOAT32),
  created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX agent_memory_task_idx ON agent_memory (task_id);

EXIT;
SQL

echo "Schema initialized successfully."
