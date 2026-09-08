-- Setup script for Oracle Hybrid Vector Search
-- Run after the Oracle container is running and setup-db.sql has been executed:
--   podman cp all_MiniLM_L12_v2.onnx oradb:/opt/oracle/dumps/
--   podman exec -i oradb sqlplus pdbadmin/Oracle123@freepdb1 < setup-hybrid-search.sql
-- Safe to re-run (skips steps that already completed).

-- 1. Load the pre-built ONNX embedding model (skip if already loaded)
DECLARE
  model_count NUMBER;
BEGIN
  SELECT COUNT(*) INTO model_count FROM USER_MINING_MODELS WHERE MODEL_NAME = 'ALL_MINILM_L12_V2';
  IF model_count = 0 THEN
    DBMS_VECTOR.LOAD_ONNX_MODEL(
      directory  => 'DM_DUMP',
      file_name  => 'all_MiniLM_L12_v2.onnx',
      model_name => 'ALL_MINILM_L12_V2'
    );
  END IF;
END;
/

-- 2. Verify the model works
SELECT VECTOR_EMBEDDING(ALL_MINILM_L12_V2 USING 'hello world' AS data) FROM DUAL;

-- 3. Create the policy documents table
CREATE TABLE IF NOT EXISTS POLICY_DOCS (
  id      VARCHAR2(36) DEFAULT sys_guid() PRIMARY KEY,
  content CLOB NOT NULL
);

-- 4. Create the hybrid vector index (drop if FAILED, skip if healthy)
DECLARE
  idx_count NUMBER;
  op_status VARCHAR2(30);
BEGIN
  SELECT COUNT(*) INTO idx_count FROM USER_INDEXES WHERE INDEX_NAME = 'POLICY_HYBRID_IDX';
  IF idx_count > 0 THEN
    SELECT DOMIDX_OPSTATUS INTO op_status FROM USER_INDEXES WHERE INDEX_NAME = 'POLICY_HYBRID_IDX';
    IF op_status = 'FAILED' THEN
      EXECUTE IMMEDIATE 'DROP INDEX POLICY_HYBRID_IDX FORCE';
      idx_count := 0;
    END IF;
  END IF;
  IF idx_count = 0 THEN
    EXECUTE IMMEDIATE 'CREATE HYBRID VECTOR INDEX POLICY_HYBRID_IDX ON POLICY_DOCS(content) PARAMETERS(''MODEL ALL_MINILM_L12_V2 VECTOR_IDXTYPE HNSW'')';
  END IF;
END;
/
