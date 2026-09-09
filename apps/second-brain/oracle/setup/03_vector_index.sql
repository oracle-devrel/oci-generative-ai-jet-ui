-- OPTIONAL — only needed at scale. A fast approximate (HNSW) vector index speeds up
-- semantic recall when agent_memory grows large. At demo scale, exact search is instant
-- and you can skip this entirely.
--
-- HNSW indexes live in a dedicated VECTOR MEMORY POOL, which defaults to 0 — so you must
-- size it first. vector_memory_size is (mostly) static, so this needs a DB restart:
--
--   As SYS:  ALTER SYSTEM SET vector_memory_size = 512M SCOPE=SPFILE;
--   Then:    docker restart ccc-oracle      (wait for healthy)
--
-- After the restart, create the index:

ALTER SESSION SET CURRENT_SCHEMA = CCC;

CREATE VECTOR INDEX agent_memory_vec_idx ON agent_memory (embedding)
  ORGANIZATION INMEMORY NEIGHBOR GRAPH
  DISTANCE COSINE
  WITH TARGET ACCURACY 95;

-- With the index present, you can switch recall() back to `FETCH APPROXIMATE FIRST k ROWS`
-- for sub-linear search.
