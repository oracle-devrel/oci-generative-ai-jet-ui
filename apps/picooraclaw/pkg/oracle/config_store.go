package oracle

import (
	"database/sql"
	"fmt"
)

// ConfigStore manages configuration in Oracle PICO_CONFIG.
type ConfigStore struct {
	db      *sql.DB
	agentID string
}

// NewConfigStore creates a new Oracle-backed config store.
func NewConfigStore(db *sql.DB, agentID string) *ConfigStore {
	return &ConfigStore{
		db:      db,
		agentID: agentID,
	}
}

// GetConfigValue retrieves a single config value by key.
func (cs *ConfigStore) GetConfigValue(key string) (string, error) {
	var value sql.NullString
	err := cs.db.QueryRow(
		"SELECT config_value FROM PICO_CONFIG WHERE config_key = :1 AND agent_id = :2",
		key, cs.agentID,
	).Scan(&value)
	if err != nil {
		if err == sql.ErrNoRows {
			return "", nil
		}
		return "", fmt.Errorf("config get failed: %w", err)
	}
	if !value.Valid {
		return "", nil
	}
	return value.String, nil
}

// SetConfigValue upserts a config value using MERGE INTO.
func (cs *ConfigStore) SetConfigValue(key, value string) error {
	_, err := cs.db.Exec(`
		MERGE INTO PICO_CONFIG c
		USING (SELECT :1 AS config_key, :2 AS agent_id FROM DUAL) src
		ON (c.config_key = src.config_key AND c.agent_id = src.agent_id)
		WHEN MATCHED THEN
			UPDATE SET config_value = :3, updated_at = CURRENT_TIMESTAMP
		WHEN NOT MATCHED THEN
			INSERT (config_key, agent_id, config_value) VALUES (:4, :5, :6)
	`, key, cs.agentID, value, key, cs.agentID, value)
	if err != nil {
		return fmt.Errorf("config set failed: %w", err)
	}
	return nil
}

// LoadConfig retrieves the full config JSON.
func (cs *ConfigStore) LoadConfig() (string, error) {
	return cs.GetConfigValue("full_config")
}

// SaveConfig stores the full config JSON.
func (cs *ConfigStore) SaveConfig(configJSON string) error {
	return cs.SetConfigValue("full_config", configJSON)
}
