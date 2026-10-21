CREATE TABLE guideline_memory (
  id              VARCHAR2(64)  PRIMARY KEY,
  tenant_id       VARCHAR2(64)  NOT NULL,
  user_id         VARCHAR2(64),
  agent_id        VARCHAR2(64),
  thread_id       VARCHAR2(64),              -- session identifier
  guideline_key   VARCHAR2(128) NOT NULL,
  guideline_value JSON          NOT NULL,
  version         NUMBER(10)    NOT NULL,
  valid_from      TIMESTAMP     NOT NULL,
  valid_until     TIMESTAMP,
  written_by      VARCHAR2(64)  NOT NULL,
  source_event_id VARCHAR2(64),
  created_at      TIMESTAMP     NOT NULL,
  deleted_at      TIMESTAMP
);

CREATE TABLE persona_memory (
  id              VARCHAR2(64)  PRIMARY KEY,
  tenant_id       VARCHAR2(64)  NOT NULL,
  user_id         VARCHAR2(64),
  agent_id        VARCHAR2(64),
  thread_id       VARCHAR2(64),
  persona_key     VARCHAR2(64)  NOT NULL,
  persona_value   JSON,                      -- nullable: erased on right-to-forget
  confidence      NUMBER(3,2),
  written_by      VARCHAR2(64)  NOT NULL,
  source_event_id VARCHAR2(64),
  valid_from      TIMESTAMP     NOT NULL,
  valid_until     TIMESTAMP,
  created_at      TIMESTAMP     NOT NULL,
  deleted_at      TIMESTAMP
);

CREATE TABLE entity_memory (
  id              VARCHAR2(64)  PRIMARY KEY,
  tenant_id       VARCHAR2(64)  NOT NULL,
  user_id         VARCHAR2(64),
  agent_id        VARCHAR2(64),
  thread_id       VARCHAR2(64),
  subject         VARCHAR2(256) NOT NULL,
  predicate       VARCHAR2(64)  NOT NULL,
  content         CLOB,                      -- nullable: erased on right-to-forget
  content_hash    VARCHAR2(64)  NOT NULL,
  content_json    JSON,
  embedding       VECTOR(384, FLOAT32),
  confidence      NUMBER(3,2)   NOT NULL,
  written_by      VARCHAR2(64)  NOT NULL,
  source_event_id VARCHAR2(64)  NOT NULL,
  version         NUMBER(10)    NOT NULL,
  superseded_by   VARCHAR2(64),
  valid_from      TIMESTAMP     NOT NULL,
  valid_until     TIMESTAMP,
  created_at      TIMESTAMP     NOT NULL,
  deleted_at      TIMESTAMP
);

CREATE TABLE conversation_memory (
  event_id        VARCHAR2(64)  PRIMARY KEY,
  tenant_id       VARCHAR2(64)  NOT NULL,
  user_id         VARCHAR2(64),
  agent_id        VARCHAR2(64),
  thread_id       VARCHAR2(64)  NOT NULL,
  run_id          VARCHAR2(64)  NOT NULL,
  turn_index      NUMBER(10)    NOT NULL,
  event_type      VARCHAR2(32)  NOT NULL,
  role            VARCHAR2(32),
  payload         JSON          NOT NULL,
  token_cost      NUMBER(10),
  latency_ms      NUMBER(10),
  retention_class VARCHAR2(16)  DEFAULT 'short' NOT NULL,
  created_at      TIMESTAMP     NOT NULL
) PARTITION BY RANGE (created_at)
  INTERVAL (NUMTODSINTERVAL(1, 'DAY'))
  ( PARTITION p0 VALUES LESS THAN (TIMESTAMP '2026-01-01 00:00:00') );

CREATE TABLE summarization_memory (
  id              VARCHAR2(64)  PRIMARY KEY,
  tenant_id       VARCHAR2(64)  NOT NULL,
  user_id         VARCHAR2(64),
  agent_id        VARCHAR2(64),
  thread_id       VARCHAR2(64),
  task_type       VARCHAR2(64)  NOT NULL,
  title           VARCHAR2(256) NOT NULL,
  summary         CLOB,                      -- nullable: erased on right-to-forget
  key_steps       JSON,
  outcome         VARCHAR2(64),
  artifacts       JSON,
  embedding       VECTOR(384, FLOAT32),
  confidence      NUMBER(3,2)   NOT NULL,
  written_by      VARCHAR2(64)  NOT NULL,
  source_event_id VARCHAR2(64)  NOT NULL,
  version         NUMBER(10)    NOT NULL,
  superseded_by   VARCHAR2(64),
  valid_from      TIMESTAMP     NOT NULL,
  valid_until     TIMESTAMP,
  completed_at    TIMESTAMP     NOT NULL,
  created_at      TIMESTAMP     NOT NULL,
  deleted_at      TIMESTAMP
);

CREATE TABLE workflow_memory (
  id               VARCHAR2(64)  PRIMARY KEY,
  tenant_id        VARCHAR2(64)  NOT NULL,
  user_id          VARCHAR2(64),
  agent_id         VARCHAR2(64),
  workflow_name    VARCHAR2(128) NOT NULL,
  description      CLOB,
  steps            JSON          NOT NULL,
  preconditions    JSON,
  expected_outcome JSON,
  success_count    NUMBER(10)    DEFAULT 0 NOT NULL,
  failure_count    NUMBER(10)    DEFAULT 0 NOT NULL,
  embedding        VECTOR(384, FLOAT32),
  confidence       NUMBER(3,2)   NOT NULL,
  written_by       VARCHAR2(64)  NOT NULL,
  source_event_id  VARCHAR2(64),
  version          NUMBER(10)    NOT NULL,
  superseded_by    VARCHAR2(64),
  valid_from       TIMESTAMP     NOT NULL,
  valid_until      TIMESTAMP,
  created_at       TIMESTAMP     NOT NULL,
  deleted_at       TIMESTAMP
);

CREATE TABLE toolbox_memory (
  id              VARCHAR2(64)  PRIMARY KEY,
  tenant_id       VARCHAR2(64)  NOT NULL,
  user_id         VARCHAR2(64),
  agent_id        VARCHAR2(64),
  tool_name       VARCHAR2(128) NOT NULL,
  tool_schema     JSON          NOT NULL,
  tool_handler    VARCHAR2(256),
  access_policy   JSON,
  usage_notes     CLOB,
  embedding       VECTOR(384, FLOAT32),
  version         NUMBER(10)    NOT NULL,
  superseded_by   VARCHAR2(64),
  valid_from      TIMESTAMP     NOT NULL,
  valid_until     TIMESTAMP,
  written_by      VARCHAR2(64)  NOT NULL,
  source_event_id VARCHAR2(64),
  created_at      TIMESTAMP     NOT NULL,
  deleted_at      TIMESTAMP
);

CREATE TABLE knowledge_base_document (
  id              VARCHAR2(64)  PRIMARY KEY,
  tenant_id       VARCHAR2(64)  NOT NULL,
  user_id         VARCHAR2(64),
  agent_id        VARCHAR2(64),
  collection      VARCHAR2(128) NOT NULL,
  title           VARCHAR2(512) NOT NULL,
  source_uri      VARCHAR2(1024),
  source_type     VARCHAR2(64)  NOT NULL,
  metadata        JSON,
  ingested_at     TIMESTAMP     NOT NULL,
  ingested_by     VARCHAR2(64)  NOT NULL,
  version         NUMBER(10)    NOT NULL,
  superseded_by   VARCHAR2(64),
  valid_from      TIMESTAMP     NOT NULL,
  valid_until     TIMESTAMP,
  created_at      TIMESTAMP     NOT NULL,
  deleted_at      TIMESTAMP
);

CREATE TABLE knowledge_base_chunk (
  id              VARCHAR2(64)  PRIMARY KEY,
  tenant_id       VARCHAR2(64)  NOT NULL,
  document_id     VARCHAR2(64)  NOT NULL,
  chunk_index     NUMBER(10)    NOT NULL,
  content         CLOB          NOT NULL,
  embedding       VECTOR(384, FLOAT32),
  metadata        JSON,
  created_at      TIMESTAMP     NOT NULL,
  deleted_at      TIMESTAMP,
  CONSTRAINT fk_kb_chunk_doc FOREIGN KEY (document_id) REFERENCES knowledge_base_document (id)
);

CREATE TABLE deletion_events (
  id          VARCHAR2(64)  DEFAULT SYS_GUID() PRIMARY KEY,
  tenant_id   VARCHAR2(64)  NOT NULL,
  user_id     VARCHAR2(64),
  scope       VARCHAR2(32)  NOT NULL,        -- 'all' | 'tenant' | 'user' | 'thread'
  deleted_at  TIMESTAMP     NOT NULL,
  reason      VARCHAR2(64)  NOT NULL,
  created_at  TIMESTAMP     DEFAULT SYSTIMESTAMP NOT NULL
);

CREATE UNIQUE INDEX idx_guideline_active
  ON guideline_memory (
    CASE WHEN valid_until IS NULL AND deleted_at IS NULL THEN tenant_id      END,
    CASE WHEN valid_until IS NULL AND deleted_at IS NULL THEN user_id        END,
    CASE WHEN valid_until IS NULL AND deleted_at IS NULL THEN agent_id       END,
    CASE WHEN valid_until IS NULL AND deleted_at IS NULL THEN thread_id      END,
    CASE WHEN valid_until IS NULL AND deleted_at IS NULL THEN guideline_key END
  );

CREATE UNIQUE INDEX idx_persona_active
  ON persona_memory (
    CASE WHEN valid_until IS NULL AND deleted_at IS NULL THEN tenant_id      END,
    CASE WHEN valid_until IS NULL AND deleted_at IS NULL THEN user_id        END,
    CASE WHEN valid_until IS NULL AND deleted_at IS NULL THEN agent_id       END,
    CASE WHEN valid_until IS NULL AND deleted_at IS NULL THEN thread_id      END,
    CASE WHEN valid_until IS NULL AND deleted_at IS NULL THEN persona_key END
  );

CREATE INDEX idx_entity_scope_active ON entity_memory (tenant_id, user_id, agent_id, thread_id, deleted_at, valid_until);

CREATE INDEX idx_entity_dedup        ON entity_memory (tenant_id, user_id, agent_id, content_hash);

CREATE INDEX idx_entity_subject      ON entity_memory (tenant_id, subject);

CREATE INDEX idx_entity_content_json ON entity_memory (JSON_VALUE(content_json, '$.entity_type'));

CREATE VECTOR INDEX idx_entity_embedding
  ON entity_memory (embedding)
  ORGANIZATION INMEMORY NEIGHBOR GRAPH
  DISTANCE COSINE
  WITH TARGET ACCURACY 95;

CREATE INDEX idx_entity_text ON entity_memory (content)
  INDEXTYPE IS CTXSYS.CONTEXT PARAMETERS ('SYNC (ON COMMIT)');

CREATE INDEX idx_conv_thread_turn ON conversation_memory (tenant_id, thread_id, turn_index);

CREATE INDEX idx_conv_run         ON conversation_memory (tenant_id, run_id, turn_index);

CREATE INDEX idx_conv_user_time   ON conversation_memory (tenant_id, user_id, created_at);

CREATE INDEX idx_summ_scope_task
  ON summarization_memory (tenant_id, user_id, agent_id, task_type, completed_at);

CREATE VECTOR INDEX idx_summ_embedding
  ON summarization_memory (embedding)
  ORGANIZATION INMEMORY NEIGHBOR GRAPH
  DISTANCE COSINE
  WITH TARGET ACCURACY 95;

CREATE INDEX idx_summ_text ON summarization_memory (summary)
  INDEXTYPE IS CTXSYS.CONTEXT PARAMETERS ('SYNC (ON COMMIT)');

CREATE INDEX idx_workflow_scope_name
  ON workflow_memory (tenant_id, user_id, agent_id, workflow_name);

CREATE VECTOR INDEX idx_workflow_embedding
  ON workflow_memory (embedding)
  ORGANIZATION INMEMORY NEIGHBOR GRAPH
  DISTANCE COSINE
  WITH TARGET ACCURACY 95;

CREATE UNIQUE INDEX idx_toolbox_active
  ON toolbox_memory (
    CASE WHEN valid_until IS NULL AND deleted_at IS NULL THEN tenant_id END,
    CASE WHEN valid_until IS NULL AND deleted_at IS NULL THEN user_id   END,
    CASE WHEN valid_until IS NULL AND deleted_at IS NULL THEN agent_id  END,
    CASE WHEN valid_until IS NULL AND deleted_at IS NULL THEN tool_name END
  );

CREATE UNIQUE INDEX idx_kb_chunk_doc_idx
  ON knowledge_base_chunk (tenant_id, document_id, chunk_index);

CREATE INDEX idx_kb_doc_collection
  ON knowledge_base_document (tenant_id, user_id, agent_id, collection, valid_until);

CREATE VECTOR INDEX idx_kb_chunk_embedding
  ON knowledge_base_chunk (embedding)
  ORGANIZATION INMEMORY NEIGHBOR GRAPH
  DISTANCE COSINE
  WITH TARGET ACCURACY 95;

CREATE INDEX idx_kb_chunk_text ON knowledge_base_chunk(content) INDEXTYPE IS CTXSYS.CONTEXT PARAMETERS ('SYNC (ON COMMIT)');

CREATE INDEX idx_kb_chunk_section ON knowledge_base_chunk (JSON_VALUE(metadata, '$.section_type'));
