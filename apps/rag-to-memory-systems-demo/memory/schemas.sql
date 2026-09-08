-- policy_memory: versioned rules, exact-match retrieval only.
CREATE TABLE policy_memory (
  policy_id         VARCHAR2(64) PRIMARY KEY,
  tenant_id         VARCHAR2(64) NOT NULL,
  policy_type       VARCHAR2(32) NOT NULL,
  policy_key        VARCHAR2(128) NOT NULL,
  policy_value      JSON NOT NULL,
  version           NUMBER NOT NULL,
  effective_from    TIMESTAMP NOT NULL,
  effective_until   TIMESTAMP,
  created_by        VARCHAR2(64) NOT NULL,
  CONSTRAINT uq_policy_version UNIQUE (tenant_id, policy_key, version)
);

CREATE INDEX idx_policy_lookup ON policy_memory (tenant_id, policy_key, effective_until);

-- preference_memory: per-user personalization, keyed upsert.
CREATE TABLE preference_memory (
  user_id     VARCHAR2(64) NOT NULL,
  tenant_id   VARCHAR2(64) NOT NULL,
  pref_key    VARCHAR2(64) NOT NULL,
  pref_value  JSON NOT NULL,
  source      VARCHAR2(32) NOT NULL,
  confidence  NUMBER(3,2),
  updated_at  TIMESTAMP NOT NULL,
  CONSTRAINT pk_preference PRIMARY KEY (user_id, tenant_id, pref_key)
);

-- fact_memory: hybrid retrieval, supersession, dedup by content_hash.
CREATE TABLE fact_memory (
  fact_id          VARCHAR2(64) PRIMARY KEY,
  tenant_id        VARCHAR2(64) NOT NULL,
  user_id          VARCHAR2(64),
  agent_id         VARCHAR2(64),
  subject          VARCHAR2(256) NOT NULL,
  predicate        VARCHAR2(64) NOT NULL,
  content          CLOB NOT NULL,
  content_hash     VARCHAR2(64) NOT NULL,
  embedding        VECTOR(384, FLOAT32),
  metadata         JSON,
  status           VARCHAR2(16) DEFAULT 'active'
                   CONSTRAINT ck_fact_status CHECK (status IN ('provisional','active','revoked')),
  source_run_id    VARCHAR2(64) NOT NULL,
  source_turn_id   VARCHAR2(64),
  confidence       NUMBER(3,2) NOT NULL,
  superseded_by    VARCHAR2(64),
  expires_at       TIMESTAMP,
  created_at       TIMESTAMP NOT NULL
);
CREATE INDEX idx_fact_scope  ON fact_memory (tenant_id, user_id, agent_id);
CREATE INDEX idx_fact_status ON fact_memory (tenant_id, status);
CREATE INDEX idx_fact_dedup  ON fact_memory (content_hash, tenant_id);

-- Oracle Text index for lexical hybrid retrieval.
-- SYNC (ON COMMIT) makes the index update at every commit so new facts are
-- immediately searchable via CONTAINS(). Default would be manual sync, which
-- would require CTX_DDL.SYNC_INDEX calls after every write.
-- This may fail with ORA-29855 if CTXAPP is not granted to the current user.
-- DDL runner should catch and warn (but continue) for this specific error.
CREATE INDEX idx_fact_text ON fact_memory (content)
  INDEXTYPE IS CTXSYS.CONTEXT
  PARAMETERS ('SYNC (ON COMMIT)');

-- episodic_memory: structured summaries with vector index over the summary.
CREATE TABLE episodic_memory (
  episode_id     VARCHAR2(64) PRIMARY KEY,
  tenant_id      VARCHAR2(64) NOT NULL,
  user_id        VARCHAR2(64),
  task_type      VARCHAR2(64) NOT NULL,
  title          VARCHAR2(256) NOT NULL,
  summary        CLOB NOT NULL,
  outcome        VARCHAR2(32) NOT NULL,
  key_steps      JSON NOT NULL,
  artifacts      JSON,
  embedding      VECTOR(384, FLOAT32),
  status         VARCHAR2(16) DEFAULT 'active'
                 CONSTRAINT ck_ep_status CHECK (status IN ('provisional','active','revoked')),
  source_run_id  VARCHAR2(64) NOT NULL,
  completed_at   TIMESTAMP NOT NULL
);
CREATE INDEX idx_ep_scope ON episodic_memory (tenant_id, task_type, completed_at);

-- Oracle Text index for lexical hybrid retrieval on episode summaries.
-- Catches verbatim tokens (ticket IDs, service names, error codes) that
-- pure vector misses. Same SYNC (ON COMMIT) pattern and ORA-29855
-- caveat as idx_fact_text.
CREATE INDEX idx_ep_text ON episodic_memory (summary)
  INDEXTYPE IS CTXSYS.CONTEXT
  PARAMETERS ('SYNC (ON COMMIT)');

-- trace_memory: append-only event log.
-- event_type CHECK covers the values the manager actually writes:
--   user_msg, model_msg              -- conversational turns
--   tool_call, tool_result           -- reserved for tool-using agents
--   turn_envelope                    -- per-turn retrieval/promotion summary
--   confirmation_synthesis           -- bare-confirmation rewrite
--   extraction_error, promotion_error -- failures surfaced in replay
CREATE TABLE trace_memory (
  trace_id     VARCHAR2(64) PRIMARY KEY,
  run_id       VARCHAR2(64) NOT NULL,
  tenant_id    VARCHAR2(64) NOT NULL,
  user_id      VARCHAR2(64),
  turn_index   NUMBER NOT NULL,
  event_type   VARCHAR2(32) NOT NULL
               CONSTRAINT ck_trace_event_type CHECK (event_type IN (
                 'user_msg', 'model_msg', 'tool_call', 'tool_result',
                 'turn_envelope', 'confirmation_synthesis',
                 'extraction_error', 'promotion_error'
               )),
  payload      JSON NOT NULL,
  token_cost   NUMBER,
  latency_ms   NUMBER,
  created_at   TIMESTAMP NOT NULL
);
CREATE INDEX idx_trace_run    ON trace_memory (run_id, turn_index);
CREATE INDEX idx_trace_tenant ON trace_memory (tenant_id, created_at);

-- deletion_events: GDPR cascade audit trail.
CREATE TABLE deletion_events (
  user_id     VARCHAR2(64) NOT NULL,
  scope       VARCHAR2(32) NOT NULL,
  deleted_at  TIMESTAMP NOT NULL,
  reason      VARCHAR2(64) NOT NULL
);
