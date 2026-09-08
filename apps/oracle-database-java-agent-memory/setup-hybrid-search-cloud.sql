-- Cloud (Autonomous Database) variant of setup-hybrid-search.sql.
-- Expected runtime context:
--   Connected as ADMIN to an Autonomous DB via wallet/mTLS.
--   A DBMS_CLOUD credential named OCI_API_KEY_CRED already exists
--     (created by the ops playbook from init/create_credential.sql.j2).
--   This file is templated by the ops playbook to fill in the Object
--     Storage URL of the ONNX model and the in-DB model name.
-- Safe to re-run (skips steps that already completed).

WHENEVER SQLERROR EXIT SQL.SQLCODE

-- 1. Load the ONNX embedding model from Object Storage (skip if already loaded)
DECLARE
  model_count NUMBER;
BEGIN
  SELECT COUNT(*) INTO model_count
    FROM USER_MINING_MODELS
   WHERE MODEL_NAME = '{{ onnx_model_name }}';
  IF model_count = 0 THEN
    DBMS_VECTOR.LOAD_ONNX_MODEL_CLOUD(
      model_name => '{{ onnx_model_name }}',
      credential => 'OCI_API_KEY_CRED',
      uri        => '{{ onnx_object_uri }}'
    );
  END IF;
END;
/

-- 2. Smoke test the model
SELECT VECTOR_EMBEDDING({{ onnx_model_name }} USING 'hello world' AS data) FROM DUAL;

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
    EXECUTE IMMEDIATE 'CREATE HYBRID VECTOR INDEX POLICY_HYBRID_IDX ON POLICY_DOCS(content) PARAMETERS(''MODEL {{ onnx_model_name }} VECTOR_IDXTYPE HNSW'')';
  END IF;
END;
/

EXIT;
