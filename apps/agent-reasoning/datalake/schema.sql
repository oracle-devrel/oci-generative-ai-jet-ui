-- =============================================================================
-- Reasoning Datalake Schema for Oracle 26ai Free
-- =============================================================================
-- Target: Oracle Database 26ai Free (container-registry.oracle.com/database/free:latest-lite)
-- Service: FREEPDB1
-- 
-- This DDL creates the full schema for storing reasoning session traces,
-- events, performance metrics, and cross-session comparisons.
--
-- Run as SYSDBA first to create the user:
--   CREATE USER reasoning IDENTIFIED BY reasoning;
--   GRANT CONNECT, RESOURCE, UNLIMITED TABLESPACE TO reasoning;
--   GRANT CREATE SESSION TO reasoning;
--   GRANT CREATE TABLE TO reasoning;
--   GRANT CREATE SEQUENCE TO reasoning;
--   GRANT CREATE VIEW TO reasoning;
-- Then connect as the reasoning user to run this script.
-- =============================================================================

-- ---------------------------------------------------------------------------
-- Sequences (for sequence_num auto-increment within sessions)
-- ---------------------------------------------------------------------------

CREATE SEQUENCE reasoning_event_seq
    START WITH 1
    INCREMENT BY 1
    NOCACHE
    NOCYCLE;


-- ---------------------------------------------------------------------------
-- Table: REASONING_SESSIONS
-- ---------------------------------------------------------------------------
-- Stores one row per reasoning session (one query + one strategy invocation).

CREATE TABLE reasoning_sessions (
    id              VARCHAR2(36)    DEFAULT SYS_GUID() PRIMARY KEY,
    query           CLOB            NOT NULL,
    strategy        VARCHAR2(64)    NOT NULL,
    model           VARCHAR2(128)   NOT NULL,
    created_at      TIMESTAMP       DEFAULT SYSTIMESTAMP NOT NULL,
    completed_at    TIMESTAMP       NULL,
    final_answer    CLOB            NULL,
    status          VARCHAR2(20)    DEFAULT 'running' NOT NULL,
    total_tokens    NUMBER(10)      NULL,
    session_metadata CLOB           NULL   -- JSON document
);

-- Indexes on frequently-queried columns
CREATE INDEX ix_sessions_strategy      ON reasoning_sessions (strategy);
CREATE INDEX ix_sessions_model         ON reasoning_sessions (model);
CREATE INDEX ix_sessions_created_at    ON reasoning_sessions (created_at);
CREATE INDEX ix_sessions_status        ON reasoning_sessions (status);
CREATE INDEX ix_sessions_strat_model   ON reasoning_sessions (strategy, model);
CREATE INDEX ix_sessions_status_created ON reasoning_sessions (status, created_at);

-- JSON check constraint on metadata
ALTER TABLE reasoning_sessions ADD CONSTRAINT chk_sessions_metadata_json
    CHECK (session_metadata IS NULL OR session_metadata IS JSON);


-- ---------------------------------------------------------------------------
-- Table: REASONING_EVENTS
-- ---------------------------------------------------------------------------
-- Stores individual StreamEvent objects emitted during reasoning.
-- The data column holds the serialized event payload as a JSON document.

CREATE TABLE reasoning_events (
    id              VARCHAR2(36)    DEFAULT SYS_GUID() PRIMARY KEY,
    session_id      VARCHAR2(36)    NOT NULL,
    event_type      VARCHAR2(64)    NOT NULL,
    sequence_num    NUMBER(10)      NOT NULL,
    data            CLOB            NOT NULL,  -- JSON payload
    created_at      TIMESTAMP       DEFAULT SYSTIMESTAMP NOT NULL,
    is_update       NUMBER(1)       DEFAULT 0  NOT NULL,

    CONSTRAINT fk_events_session
        FOREIGN KEY (session_id)
        REFERENCES reasoning_sessions (id)
        ON DELETE CASCADE
);

-- Indexes
CREATE INDEX ix_events_session_id   ON reasoning_events (session_id);
CREATE INDEX ix_events_session_seq  ON reasoning_events (session_id, sequence_num);
CREATE INDEX ix_events_type         ON reasoning_events (event_type);

-- JSON check constraint on data
ALTER TABLE reasoning_events ADD CONSTRAINT chk_events_data_json
    CHECK (data IS JSON);


-- ---------------------------------------------------------------------------
-- Table: REASONING_METRICS
-- ---------------------------------------------------------------------------
-- Performance metrics tied 1:1 to a reasoning session.

CREATE TABLE reasoning_metrics (
    id              VARCHAR2(36)    DEFAULT SYS_GUID() PRIMARY KEY,
    session_id      VARCHAR2(36)    NOT NULL,
    ttft_ms         NUMBER(12,3)    NULL,   -- Time to first token (ms)
    total_ms        NUMBER(12,3)    NULL,   -- Total duration (ms)
    tokens_per_sec  NUMBER(10,2)    NULL,   -- Throughput
    token_count     NUMBER(10)      NULL,   -- Total tokens generated
    model           VARCHAR2(128)   NULL,

    CONSTRAINT fk_metrics_session
        FOREIGN KEY (session_id)
        REFERENCES reasoning_sessions (id)
        ON DELETE CASCADE,

    CONSTRAINT uq_metrics_session
        UNIQUE (session_id)
);

CREATE INDEX ix_metrics_session_id ON reasoning_metrics (session_id);


-- ---------------------------------------------------------------------------
-- Table: REASONING_COMPARISONS
-- ---------------------------------------------------------------------------
-- Named groups of sessions for side-by-side comparison.
-- session_ids is stored as a JSON array of UUID strings.

CREATE TABLE reasoning_comparisons (
    id              VARCHAR2(36)    DEFAULT SYS_GUID() PRIMARY KEY,
    name            VARCHAR2(256)   NOT NULL,
    query           CLOB            NULL,
    created_at      TIMESTAMP       DEFAULT SYSTIMESTAMP NOT NULL,
    session_ids     CLOB            NOT NULL   -- JSON array ["uuid1", "uuid2", ...]
);

-- JSON check constraint on session_ids
ALTER TABLE reasoning_comparisons ADD CONSTRAINT chk_comparisons_ids_json
    CHECK (session_ids IS JSON);


-- ---------------------------------------------------------------------------
-- Views
-- ---------------------------------------------------------------------------

-- Aggregated session summary with event counts and metrics
CREATE OR REPLACE VIEW v_session_summary AS
SELECT
    s.id,
    s.query,
    s.strategy,
    s.model,
    s.status,
    s.created_at,
    s.completed_at,
    s.total_tokens,
    (SELECT COUNT(*) FROM reasoning_events e WHERE e.session_id = s.id) AS event_count,
    m.ttft_ms,
    m.total_ms,
    m.tokens_per_sec,
    m.token_count
FROM reasoning_sessions s
LEFT JOIN reasoning_metrics m ON m.session_id = s.id;


-- Strategy-level aggregate statistics
CREATE OR REPLACE VIEW v_strategy_stats AS
SELECT
    s.strategy,
    s.model,
    COUNT(*)                        AS session_count,
    AVG(m.total_ms)                 AS avg_duration_ms,
    AVG(m.ttft_ms)                  AS avg_ttft_ms,
    AVG(m.tokens_per_sec)           AS avg_tokens_per_sec,
    AVG(m.token_count)              AS avg_token_count,
    MIN(s.created_at)               AS first_session,
    MAX(s.created_at)               AS last_session
FROM reasoning_sessions s
LEFT JOIN reasoning_metrics m ON m.session_id = s.id
WHERE s.status = 'completed'
GROUP BY s.strategy, s.model;


-- =============================================================================
-- End of schema
-- =============================================================================
