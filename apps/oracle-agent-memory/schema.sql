-- oracle-agent-memory schema
-- Run against an Oracle Database 26ai instance (Autonomous, on-prem, or container).
-- The vector dimension (1024) matches OCI's cohere.embed-english-v3.0 model.
-- If you swap embedding models, update the dimension to match.

-- Episodic memory: every post you've ever written
CREATE TABLE posts (
    id            VARCHAR2(36) PRIMARY KEY,
    user_id       VARCHAR2(64) NOT NULL,
    platform      VARCHAR2(32) NOT NULL,
    topic         VARCHAR2(256),
    content       CLOB NOT NULL,
    embedding     VECTOR(1024, FLOAT32),
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_deleted    NUMBER(1) DEFAULT 0
);

CREATE VECTOR INDEX posts_hnsw_idx ON posts (embedding)
    ORGANIZATION INMEMORY NEIGHBOR GRAPH
    DISTANCE COSINE
    PARAMETERS (TYPE HNSW, NEIGHBORS 32, EFCONSTRUCTION 200);

CREATE INDEX posts_user_platform_idx ON posts (user_id, platform);

-- Semantic memory: the style profile per user
CREATE TABLE style_profile (
    user_id       VARCHAR2(64) PRIMARY KEY,
    profile       JSON NOT NULL,
    updated_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    version       NUMBER(10) DEFAULT 1
);

-- Reflective memory: what changed and when
CREATE TABLE reflections (
    id            VARCHAR2(36) PRIMARY KEY,
    user_id       VARCHAR2(64) NOT NULL,
    triggered_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    posts_window  JSON NOT NULL,
    diff          JSON NOT NULL,
    profile_after JSON NOT NULL
);

CREATE INDEX reflections_user_idx ON reflections (user_id, triggered_at);
