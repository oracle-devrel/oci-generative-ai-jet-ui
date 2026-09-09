-- Run as the `idp` user.
-- Core relational schema: documents + per-doc-type structured fields.

CREATE TABLE documents (
  id                RAW(16)         DEFAULT SYS_GUID() PRIMARY KEY,
  doc_type          VARCHAR2(16)    DEFAULT 'unknown' NOT NULL,
  status            VARCHAR2(32)    DEFAULT 'pending' NOT NULL,
  original_filename VARCHAR2(512)   NOT NULL,
  mime_type         VARCHAR2(128)   NOT NULL,
  byte_size         NUMBER          NOT NULL,
  page_count        NUMBER,
  language          VARCHAR2(8),
  failed_reason     VARCHAR2(512),
  created_at        TIMESTAMP       DEFAULT SYSTIMESTAMP NOT NULL,
  updated_at        TIMESTAMP       DEFAULT SYSTIMESTAMP NOT NULL,
  file_blob         BLOB            NOT NULL,
  extracted_text    CLOB,
  embedding         VECTOR(384, FLOAT32),
  CONSTRAINT documents_doc_type_chk
    CHECK (doc_type IN ('invoice', 'purchase_order', 'delivery_note', 'unknown')),
  CONSTRAINT documents_status_chk
    CHECK (status IN ('pending','text_extracted','classified','fields_extracted','embedded','done','failed'))
);

CREATE INDEX documents_list_idx
  ON documents (doc_type, status, created_at DESC);

CREATE TABLE document_fields (
  document_id RAW(16)        PRIMARY KEY,
  payload     JSON           NOT NULL,
  created_at  TIMESTAMP      DEFAULT SYSTIMESTAMP NOT NULL,
  updated_at  TIMESTAMP      DEFAULT SYSTIMESTAMP NOT NULL,
  CONSTRAINT document_fields_document_fk
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
);

CREATE VECTOR INDEX documents_embedding_idx
  ON documents (embedding)
  ORGANIZATION INMEMORY NEIGHBOR GRAPH
  DISTANCE COSINE
  WITH TARGET ACCURACY 95;

BEGIN
  CTX_DDL.CREATE_PREFERENCE('idp_text_lexer', 'BASIC_LEXER');
EXCEPTION
  WHEN OTHERS THEN
    IF SQLERRM LIKE '%DRG-10701%' THEN NULL; ELSE RAISE; END IF;
END;
/

CREATE INDEX documents_text_idx
  ON documents (extracted_text)
  INDEXTYPE IS CTXSYS.CONTEXT
  PARAMETERS ('LEXER idp_text_lexer SYNC (ON COMMIT)');

CREATE OR REPLACE TRIGGER documents_updated_at_trg
  BEFORE UPDATE ON documents
  FOR EACH ROW
BEGIN
  :NEW.updated_at := SYSTIMESTAMP;
END;
/

CREATE OR REPLACE TRIGGER document_fields_updated_at_trg
  BEFORE UPDATE ON document_fields
  FOR EACH ROW
BEGIN
  :NEW.updated_at := SYSTIMESTAMP;
END;
/
