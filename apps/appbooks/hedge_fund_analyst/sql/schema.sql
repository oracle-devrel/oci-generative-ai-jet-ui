CREATE TABLE HF_DESKS (desk VARCHAR2(20) PRIMARY KEY, nav NUMBER NOT NULL)
-- @statement
CREATE TABLE HF_PORTFOLIOS (portfolio_id NUMBER PRIMARY KEY, desk VARCHAR2(20) REFERENCES HF_DESKS, name VARCHAR2(100))
-- @statement
CREATE TABLE HF_ISSUERS (issuer_id NUMBER PRIMARY KEY, alias VARCHAR2(100), root_lei VARCHAR2(20))
-- @statement
CREATE TABLE HF_ENTITIES (lei VARCHAR2(20) PRIMARY KEY, name VARCHAR2(250), issuer_id NUMBER REFERENCES HF_ISSUERS, source VARCHAR2(1000))
-- @statement
CREATE TABLE HF_RELATIONSHIPS (edge_id NUMBER PRIMARY KEY, parent_lei VARCHAR2(20) REFERENCES HF_ENTITIES, child_lei VARCHAR2(20) REFERENCES HF_ENTITIES, relationship_type VARCHAR2(60), source VARCHAR2(1000))
-- @statement
CREATE TABLE HF_INSTRUMENTS (instrument_id NUMBER PRIMARY KEY, lei VARCHAR2(20) REFERENCES HF_ENTITIES, ticker VARCHAR2(30), asset_class VARCHAR2(20), duration NUMBER, adv_units NUMBER, beta NUMBER)
-- @statement
CREATE TABLE HF_POSITIONS (position_id NUMBER PRIMARY KEY, instrument_id NUMBER REFERENCES HF_INSTRUMENTS, portfolio_id NUMBER REFERENCES HF_PORTFOLIOS, desk VARCHAR2(20), quantity NUMBER, market_value NUMBER)
-- @statement
CREATE TABLE HF_COLLATERAL (position_id NUMBER PRIMARY KEY REFERENCES HF_POSITIONS, desk VARCHAR2(20), eligible_value NUMBER)
-- @statement
CREATE TABLE HF_PRICES (instrument_id NUMBER REFERENCES HF_INSTRUMENTS, price_date DATE, price NUMBER, PRIMARY KEY(instrument_id,price_date))
-- @statement
CREATE TABLE HF_NOTES (note_id NUMBER PRIMARY KEY, instrument_id NUMBER REFERENCES HF_INSTRUMENTS, desk VARCHAR2(20), title VARCHAR2(200), body CLOB, created_at TIMESTAMP DEFAULT SYSTIMESTAMP)
-- @statement
CREATE TABLE HF_CHUNKS (chunk_id NUMBER PRIMARY KEY, note_id NUMBER REFERENCES HF_NOTES, instrument_id NUMBER, desk VARCHAR2(20), passage VARCHAR2(4000), embedding VECTOR(384,FLOAT32))
-- @statement
CREATE TABLE HF_SEMANTICS (metric VARCHAR2(60) PRIMARY KEY, definition VARCHAR2(2000), sql_template CLOB, source_sql_id VARCHAR2(13), source_sql CLOB, mined_features VARCHAR2(2000), status VARCHAR2(20), version NUMBER, approved_by VARCHAR2(100), mined_at TIMESTAMP DEFAULT SYSTIMESTAMP)
-- @statement
CREATE TABLE HF_GOLDEN (question_id NUMBER PRIMARY KEY, desk VARCHAR2(20), question VARCHAR2(1000), metric VARCHAR2(60), group_name VARCHAR2(100), expected_number NUMBER, expected_text VARCHAR2(2000), tolerance NUMBER, method VARCHAR2(30))
-- @statement
CREATE TABLE HF_CAPABILITIES (component VARCHAR2(60) PRIMARY KEY, state VARCHAR2(30), detail VARCHAR2(2000))
-- @statement
CREATE TABLE HF_LOCAL_HISTORY (thread_id VARCHAR2(80), agent VARCHAR2(20), seq NUMBER GENERATED ALWAYS AS IDENTITY, role VARCHAR2(20), content CLOB, created_at TIMESTAMP DEFAULT SYSTIMESTAMP)
-- @statement
CREATE TABLE HF_RUNS (run_id VARCHAR2(80) PRIMARY KEY, thread_id VARCHAR2(80), payload CLOB CHECK(payload IS JSON), created_at TIMESTAMP DEFAULT SYSTIMESTAMP)
-- @statement
-- SQL property graphs run with definer rights, so desk-scoped vertices must come from
-- views bound to the authenticated end user. Base tables would expose every desk.
-- Drop before create: on 23.26.2, revalidating a graph made invalid by a view change
-- restored a stale pre-REPLACE definition (base tables). DROP + CREATE leaves none.
DROP PROPERTY GRAPH HF_GRAPH
-- @statement
CREATE OR REPLACE VIEW HF_DESKS_SEC AS SELECT * FROM HF_DESKS WHERE desk=CASE SYS_CONTEXT('USERENV','AUTHENTICATED_IDENTITY') WHEN 'hf_credit' THEN 'Credit' WHEN 'hf_markets' THEN 'Markets' ELSE '--unauthorized--' END
-- @statement
CREATE OR REPLACE VIEW HF_PORTFOLIOS_SEC AS SELECT * FROM HF_PORTFOLIOS WHERE desk=CASE SYS_CONTEXT('USERENV','AUTHENTICATED_IDENTITY') WHEN 'hf_credit' THEN 'Credit' WHEN 'hf_markets' THEN 'Markets' ELSE '--unauthorized--' END
-- @statement
CREATE OR REPLACE VIEW HF_POSITIONS_SEC AS SELECT * FROM HF_POSITIONS WHERE desk=CASE SYS_CONTEXT('USERENV','AUTHENTICATED_IDENTITY') WHEN 'hf_credit' THEN 'Credit' WHEN 'hf_markets' THEN 'Markets' ELSE '--unauthorized--' END
-- @statement
CREATE PROPERTY GRAPH HF_GRAPH
 VERTEX TABLES (
 HF_ISSUERS KEY(issuer_id) LABEL Issuer PROPERTIES(issuer_id,alias,root_lei),
 HF_ENTITIES KEY(lei) LABEL LegalEntity PROPERTIES(lei,name,source),
 HF_INSTRUMENTS KEY(instrument_id) LABEL Instrument PROPERTIES(instrument_id,ticker,asset_class),
 HF_POSITIONS_SEC AS POSITIONS KEY(position_id) LABEL Position PROPERTIES(position_id,market_value,desk),
 HF_PORTFOLIOS_SEC AS PORTFOLIOS KEY(portfolio_id) LABEL Portfolio PROPERTIES(portfolio_id,name,desk),
 HF_DESKS_SEC AS DESKS KEY(desk) LABEL Desk PROPERTIES(desk,nav))
 EDGE TABLES (
 HF_ENTITIES AS ISSUED_BY KEY(lei) SOURCE KEY(issuer_id) REFERENCES HF_ISSUERS(issuer_id) DESTINATION KEY(lei) REFERENCES HF_ENTITIES(lei) LABEL HasEntity NO PROPERTIES,
 HF_RELATIONSHIPS KEY(edge_id) SOURCE KEY(parent_lei) REFERENCES HF_ENTITIES(lei) DESTINATION KEY(child_lei) REFERENCES HF_ENTITIES(lei) LABEL ParentOf PROPERTIES(relationship_type,source),
 HF_INSTRUMENTS AS ISSUES KEY(instrument_id) SOURCE KEY(lei) REFERENCES HF_ENTITIES(lei) DESTINATION KEY(instrument_id) REFERENCES HF_INSTRUMENTS(instrument_id) LABEL Issues NO PROPERTIES,
 HF_POSITIONS_SEC AS HELD_IN KEY(position_id) SOURCE KEY(instrument_id) REFERENCES HF_INSTRUMENTS(instrument_id) DESTINATION KEY(position_id) REFERENCES POSITIONS(position_id) LABEL HeldIn NO PROPERTIES,
 HF_POSITIONS_SEC AS BELONGS_TO KEY(position_id) SOURCE KEY(position_id) REFERENCES POSITIONS(position_id) DESTINATION KEY(portfolio_id) REFERENCES PORTFOLIOS(portfolio_id) LABEL BelongsTo NO PROPERTIES,
 HF_PORTFOLIOS_SEC AS MANAGED_BY KEY(portfolio_id) SOURCE KEY(portfolio_id) REFERENCES PORTFOLIOS(portfolio_id) DESTINATION KEY(desk) REFERENCES DESKS(desk) LABEL ManagedBy NO PROPERTIES)
