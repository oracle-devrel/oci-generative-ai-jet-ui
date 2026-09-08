-- ============================================================================
-- init_db.sql
-- ----------------------------------------------------------------------------
-- One-time database configuration for the RAG demo.
--
-- Allocates 512 MB of vector memory to enable in-memory HNSW (Hierarchical
-- Navigable Small World) vector indexes. Without this, the seed script falls
-- back to IVF (Inverted File Flat) indexes, which work fine but trade memory
-- residency for slightly slower searches at scale.
--
-- Required: must be run as SYSDBA. The Makefile target `make db-init` does
-- this automatically. To run manually:
--
--     docker exec -it oracle-26ai-rag sqlplus / as sysdba
--     SQL> @/path/to/init_db.sql
--
-- The database will shut down and restart, which takes about 60 seconds.
-- ============================================================================

ALTER SYSTEM SET VECTOR_MEMORY_SIZE = 512M SCOPE = SPFILE;

SHUTDOWN IMMEDIATE
STARTUP

-- Verify the setting took effect.
SHOW PARAMETER vector_memory_size;

EXIT;
