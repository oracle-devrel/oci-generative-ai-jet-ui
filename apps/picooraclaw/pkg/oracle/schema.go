package oracle

import (
	"database/sql"
	"fmt"
	"strings"

	"github.com/jasperan/picooraclaw/pkg/logger"
)

// Table DDL statements with PICO_ prefix
var tableDDL = map[string]string{
	"PICO_META": `CREATE TABLE PICO_META (
        meta_key   VARCHAR2(255) PRIMARY KEY,
        meta_value VARCHAR2(4000),
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )`,

	"PICO_MEMORIES": `CREATE TABLE PICO_MEMORIES (
        memory_id    VARCHAR2(64) PRIMARY KEY,
        agent_id     VARCHAR2(64) NOT NULL,
        content      CLOB,
        embedding    VECTOR,
        importance   NUMBER(3,2) DEFAULT 0.5,
        category     VARCHAR2(255),
        access_count NUMBER DEFAULT 0,
        created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        accessed_at  TIMESTAMP,
        updated_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )`,

	"PICO_DAILY_NOTES": `CREATE TABLE PICO_DAILY_NOTES (
        note_id    VARCHAR2(64) PRIMARY KEY,
        agent_id   VARCHAR2(64) NOT NULL,
        note_date  DATE NOT NULL,
        content    CLOB,
        embedding  VECTOR,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )`,

	"PICO_SESSIONS": `CREATE TABLE PICO_SESSIONS (
        session_key VARCHAR2(255) PRIMARY KEY,
        agent_id    VARCHAR2(64) NOT NULL,
        messages    CLOB,
        summary     CLOB,
        created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )`,

	"PICO_STATE": `CREATE TABLE PICO_STATE (
        state_key   VARCHAR2(255) NOT NULL,
        agent_id    VARCHAR2(64) NOT NULL,
        state_value VARCHAR2(4000),
        updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (state_key, agent_id)
    )`,

	"PICO_CONFIG": `CREATE TABLE PICO_CONFIG (
        config_key   VARCHAR2(255) NOT NULL,
        agent_id     VARCHAR2(64) NOT NULL,
        config_value CLOB,
        updated_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (config_key, agent_id)
    )`,

	"PICO_PROMPTS": `CREATE TABLE PICO_PROMPTS (
        prompt_name VARCHAR2(255) NOT NULL,
        agent_id    VARCHAR2(64) NOT NULL,
        content     CLOB,
        updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (prompt_name, agent_id)
    )`,

	"PICO_TRANSCRIPTS": `CREATE TABLE PICO_TRANSCRIPTS (
        id           NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        session_key  VARCHAR2(255),
        agent_id     VARCHAR2(64),
        sequence_num NUMBER,
        role         VARCHAR2(32),
        content      CLOB,
        created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )`,
}

// Regular index DDL
var indexDDL = []string{
	"CREATE INDEX IDX_PICO_MEMORIES_AGENT ON PICO_MEMORIES(agent_id)",
	"CREATE INDEX IDX_PICO_DAILY_AGENT_DATE ON PICO_DAILY_NOTES(agent_id, note_date)",
	"CREATE INDEX IDX_PICO_SESSIONS_AGENT ON PICO_SESSIONS(agent_id)",
	"CREATE INDEX IDX_PICO_TRANSCRIPTS_SESSION ON PICO_TRANSCRIPTS(session_key)",
	"CREATE INDEX IDX_PICO_STATE_AGENT ON PICO_STATE(agent_id)",
	"CREATE INDEX IDX_PICO_MEMORIES_AGENT_CAT ON PICO_MEMORIES(agent_id, category)",
}

// Vector index DDL
var vectorIndexDDL = []string{
	`CREATE VECTOR INDEX IDX_PICO_MEMORIES_VEC ON PICO_MEMORIES(embedding)
     ORGANIZATION NEIGHBOR PARTITIONS
     DISTANCE COSINE
     WITH TARGET ACCURACY 95`,
	`CREATE VECTOR INDEX IDX_PICO_DAILY_NOTES_VEC ON PICO_DAILY_NOTES(embedding)
     ORGANIZATION NEIGHBOR PARTITIONS
     DISTANCE COSINE
     WITH TARGET ACCURACY 95`,
}

// InitSchema creates all tables and indexes idempotently.
func InitSchema(db *sql.DB) error {
	logger.InfoC("oracle", "Initializing Oracle schema...")

	// Create tables
	tableOrder := []string{
		"PICO_META", "PICO_MEMORIES", "PICO_DAILY_NOTES", "PICO_SESSIONS",
		"PICO_STATE", "PICO_CONFIG", "PICO_PROMPTS", "PICO_TRANSCRIPTS",
	}

	for _, tableName := range tableOrder {
		ddl := tableDDL[tableName]
		if _, err := db.Exec(ddl); err != nil {
			if isORA00955(err) {
				logger.DebugCF("oracle", "Table already exists", map[string]interface{}{"table": tableName})
			} else {
				return fmt.Errorf("failed to create table %s: %w", tableName, err)
			}
		} else {
			logger.InfoCF("oracle", "Created table", map[string]interface{}{"table": tableName})
		}
	}

	// Create regular indexes
	for _, ddl := range indexDDL {
		if _, err := db.Exec(ddl); err != nil {
			if isORA00955(err) || isORA01408(err) {
				// Index already exists
			} else {
				logger.WarnCF("oracle", "Index creation warning", map[string]interface{}{"error": err.Error()})
			}
		}
	}

	// Create vector indexes
	for _, ddl := range vectorIndexDDL {
		if _, err := db.Exec(ddl); err != nil {
			if isORA00955(err) || isORA01408(err) {
				// Index already exists
			} else {
				logger.WarnCF("oracle", "Vector index creation warning", map[string]interface{}{"error": err.Error()})
			}
		}
	}

	// Set schema version
	setSchemaVersion(db, "1.0.0")

	logger.InfoC("oracle", "Schema initialization complete")
	return nil
}

// setSchemaVersion updates or inserts the schema version in PICO_META.
func setSchemaVersion(db *sql.DB, version string) {
	_, err := db.Exec(`
        MERGE INTO PICO_META m
        USING (SELECT 'schema_version' AS meta_key FROM DUAL) s
        ON (m.meta_key = s.meta_key)
        WHEN MATCHED THEN
            UPDATE SET meta_value = :1, updated_at = CURRENT_TIMESTAMP
        WHEN NOT MATCHED THEN
            INSERT (meta_key, meta_value) VALUES ('schema_version', :2)
    `, version, version)
	if err != nil {
		logger.WarnCF("oracle", "Failed to set schema version", map[string]interface{}{"error": err.Error()})
	}
}

// isORA00955 checks if the error is ORA-00955 (name already used by existing object).
func isORA00955(err error) bool {
	return strings.Contains(err.Error(), "ORA-00955")
}

// isORA01408 checks if the error is ORA-01408 (such column list already indexed).
func isORA01408(err error) bool {
	return strings.Contains(err.Error(), "ORA-01408")
}
