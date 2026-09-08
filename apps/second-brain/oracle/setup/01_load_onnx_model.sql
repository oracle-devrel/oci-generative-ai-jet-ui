-- Run ONCE after the DB is up (not auto-run — it needs a downloaded model file).
-- Registers an in-DATABASE embedding model named MINILM (384-dim). No external API calls —
-- embeddings are generated inside Oracle. (Great talking point: "the DB does the embeddings.")
--
-- Prereq (see README → "Load the embedding model"):
--   1. Download Oracle's prebuilt all-MiniLM-L12-v2 ONNX model.
--   2. Place it where the DB can read it and create a DIRECTORY object 'VEC_MODELS' over it.

BEGIN
  DBMS_VECTOR.LOAD_ONNX_MODEL(
    directory  => 'VEC_MODELS',
    file_name  => 'all_MiniLM_L12_v2.onnx',
    model_name => 'MINILM',
    metadata   => JSON('{
      "function"        : "embedding",
      "embeddingOutput" : "embedding",
      "input"           : { "input": ["DATA"] }
    }')
  );
END;
/

-- smoke test — should return a 384-dim vector:
-- SELECT VECTOR_EMBEDDING(MINILM USING 'hello world' AS DATA) AS v FROM dual;
