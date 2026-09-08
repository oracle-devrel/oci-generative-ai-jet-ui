-- retrieval.sql
--
-- The complete retrieval layer for the RAG demo. Eight lines of SQL.
-- Runs entirely inside Oracle AI Database 26ai. No external embedding
-- service. No separate vector store. No application-side merging.
--
-- 1. VECTOR_EMBEDDING(...) calls the all-MiniLM-L12-v2 ONNX model that
--    was loaded into the database with DBMS_VECTOR.LOAD_ONNX_MODEL.
--    It returns a 384-dimension FLOAT32 vector for the user's question.
--
-- 2. VECTOR_DISTANCE(...) compares that question vector against every
--    chunk vector using cosine similarity. The HNSW vector index makes
--    this fast.
--
-- 3. FETCH APPROX FIRST 5 ROWS ONLY tells the optimizer to use the
--    HNSW index for an Approximate Nearest Neighbor scan.
--
-- Bind variable :question is the user's question text.

SELECT
    chunk_text,
    source_page,
    VECTOR_DISTANCE(
        embedding,
        VECTOR_EMBEDDING(ALL_MINILM_L12_V2 USING :question AS data),
        COSINE
    ) AS distance
FROM DOC_CHUNKS
ORDER BY distance
FETCH APPROX FIRST 5 ROWS ONLY;
