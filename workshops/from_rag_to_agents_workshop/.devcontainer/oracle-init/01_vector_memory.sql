-- Set vector memory pool for HNSW index support
-- This runs automatically on first container startup via container-entrypoint-initdb.d
-- Use SCOPE=SPFILE so it takes effect on next restart (Oracle Free cannot resize SGA dynamically)
ALTER SYSTEM SET vector_memory_size = 1G SCOPE=SPFILE;
