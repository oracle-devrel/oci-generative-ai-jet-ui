CREATE TABLE agent_sessions (
    session_id      VARCHAR2(64) PRIMARY KEY,
    user_label      VARCHAR2(200),
    created_at      TIMESTAMP DEFAULT SYSTIMESTAMP,
    last_active_at  TIMESTAMP DEFAULT SYSTIMESTAMP
);

CREATE TABLE working_memory (
    wm_id        NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    session_id   VARCHAR2(64) REFERENCES agent_sessions(session_id),
    key          VARCHAR2(128),
    value_json   CLOB CHECK (value_json IS JSON),
    created_at   TIMESTAMP DEFAULT SYSTIMESTAMP,
    expires_at   TIMESTAMP
);

CREATE INDEX idx_wm_session_key ON working_memory(session_id, key);

CREATE TABLE episodic_memory (
    em_id        NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    session_id   VARCHAR2(64) REFERENCES agent_sessions(session_id),
    turn_index   NUMBER,
    role         VARCHAR2(16),
    content      CLOB,
    tool_name    VARCHAR2(64),
    tool_args    CLOB CHECK (tool_args IS JSON),
    created_at   TIMESTAMP DEFAULT SYSTIMESTAMP,
    embedding    VECTOR(384, FLOAT32)
);

CREATE INDEX idx_em_session ON episodic_memory(session_id, turn_index);

CREATE TABLE semantic_memory (
    sm_id        NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    fact_type    VARCHAR2(32),
    subject_key  VARCHAR2(200),
    summary      CLOB,
    source_json  CLOB CHECK (source_json IS JSON),
    embedding    VECTOR(384, FLOAT32),
    created_at   TIMESTAMP DEFAULT SYSTIMESTAMP
);

CREATE INDEX idx_sm_type_key ON semantic_memory(fact_type, subject_key);
