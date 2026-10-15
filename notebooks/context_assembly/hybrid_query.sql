WITH vec_pool AS (
  SELECT c.id, ROW_NUMBER() OVER (
           ORDER BY VECTOR_DISTANCE(c.embedding,
             VECTOR_EMBEDDING(ALL_MINILM_L12_V2 USING :query AS DATA), COSINE), c.id) AS vec_rank
    FROM knowledge_base_chunk AS OF SCN :scn c
    JOIN knowledge_base_document AS OF SCN :scn d ON d.id = c.document_id
   WHERE d.collection IN (:collection1,:collection2)
     AND d.valid_from <= :at AND (d.valid_until IS NULL OR d.valid_until > :at) AND d.deleted_at IS NULL AND c.deleted_at IS NULL
     AND (d.user_id IS NULL OR d.user_id = :user_id) AND (d.agent_id IS NULL OR d.agent_id = :agent_id)
     AND COALESCE(JSON_VALUE(c.metadata, '$.section_type'),'body') <> 'references'
   ORDER BY VECTOR_DISTANCE(c.embedding,
            VECTOR_EMBEDDING(ALL_MINILM_L12_V2 USING :query AS DATA), COSINE), c.id
   FETCH FIRST 50 ROWS ONLY),
lex_pool AS (
  -- DENSE_RANK, not ROW_NUMBER: Oracle Text SCORE() is a coarse integer and ties are
  -- common on short chunks. ROW_NUMBER would order tied chunks arbitrarily and RRF would
  -- read that arbitrary order as signal.
  SELECT c.id, DENSE_RANK() OVER (ORDER BY SCORE(1) DESC) AS lex_rank
    FROM knowledge_base_chunk AS OF SCN :scn c
    JOIN knowledge_base_document AS OF SCN :scn d ON d.id = c.document_id
   WHERE CONTAINS(c.content, :lex_query, 1) > 0
     AND d.collection IN (:collection1,:collection2)
     AND d.valid_from <= :at AND (d.valid_until IS NULL OR d.valid_until > :at) AND d.deleted_at IS NULL AND c.deleted_at IS NULL
     AND (d.user_id IS NULL OR d.user_id = :user_id) AND (d.agent_id IS NULL OR d.agent_id = :agent_id)
     AND COALESCE(JSON_VALUE(c.metadata, '$.section_type'),'body') <> 'references'
   ORDER BY SCORE(1) DESC, c.id
   FETCH FIRST 50 ROWS ONLY),
fused AS (
  SELECT COALESCE(v.id, l.id) AS id,
         COALESCE(1/(60 + v.vec_rank), 0) + COALESCE(1/(60 + l.lex_rank), 0) AS rrf_score
    FROM vec_pool v FULL OUTER JOIN lex_pool l ON v.id = l.id),
candidates AS (
  SELECT id, rrf_score FROM fused ORDER BY rrf_score DESC, id FETCH FIRST 40 ROWS ONLY)
SELECT c.id, c.content, c.metadata, d.id AS document_id, d.title, d.source_uri, d.version,
       k.rrf_score,
       PREDICTION(BGE_RERANKER USING :query AS FIRST_INPUT,
                  d.title || '. ' || c.content AS SECOND_INPUT) AS rerank_score
  FROM candidates k
  JOIN knowledge_base_chunk AS OF SCN :scn c    ON c.id = k.id
  JOIN knowledge_base_document AS OF SCN :scn d ON d.id = c.document_id
 ORDER BY rerank_score DESC, c.id
-- tenant_id appended by RLS on every table reference
