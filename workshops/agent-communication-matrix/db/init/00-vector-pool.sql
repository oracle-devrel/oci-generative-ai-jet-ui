-- 00-vector-pool.sql
-- Configure the vector memory pool before any vector index can be created.
-- This runs against the CDB root because vector_memory_size is an
-- instance-wide parameter, not a PDB-level setting.

ALTER SESSION SET CONTAINER = CDB$ROOT;
ALTER SYSTEM SET vector_memory_size = 1G SCOPE=SPFILE;
