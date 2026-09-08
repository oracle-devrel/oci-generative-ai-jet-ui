package oracle

import (
	"database/sql"
	"fmt"
	"sync"
	"time"

	"github.com/jasperan/picooraclaw/pkg/logger"
)

// StateStore implements StateManagerInterface backed by Oracle PICO_STATE table.
type StateStore struct {
	db      *sql.DB
	agentID string
	cache   map[string]string
	mu      sync.RWMutex
}

// NewStateStore creates a new Oracle-backed state store.
func NewStateStore(db *sql.DB, agentID string) *StateStore {
	ss := &StateStore{
		db:      db,
		agentID: agentID,
		cache:   make(map[string]string),
	}
	ss.loadAll()
	return ss
}

// Set upserts a key-value pair using MERGE INTO.
func (ss *StateStore) Set(key, value string) error {
	ss.mu.Lock()
	defer ss.mu.Unlock()

	_, err := ss.db.Exec(`
		MERGE INTO PICO_STATE s
		USING (SELECT :1 AS state_key, :2 AS agent_id FROM DUAL) src
		ON (s.state_key = src.state_key AND s.agent_id = src.agent_id)
		WHEN MATCHED THEN
			UPDATE SET state_value = :3, updated_at = CURRENT_TIMESTAMP
		WHEN NOT MATCHED THEN
			INSERT (state_key, agent_id, state_value) VALUES (:4, :5, :6)
	`, key, ss.agentID, value, key, ss.agentID, value)

	if err != nil {
		return fmt.Errorf("state set failed: %w", err)
	}

	ss.cache[key] = value
	return nil
}

// Get retrieves a value by key, using cache first.
func (ss *StateStore) Get(key string) string {
	ss.mu.RLock()
	if v, ok := ss.cache[key]; ok {
		ss.mu.RUnlock()
		return v
	}
	ss.mu.RUnlock()

	var value sql.NullString
	err := ss.db.QueryRow(
		"SELECT state_value FROM PICO_STATE WHERE state_key = :1 AND agent_id = :2",
		key, ss.agentID,
	).Scan(&value)
	if err != nil || !value.Valid {
		return ""
	}

	ss.mu.Lock()
	ss.cache[key] = value.String
	ss.mu.Unlock()
	return value.String
}

// SetLastChannel implements StateManagerInterface.
func (ss *StateStore) SetLastChannel(channel string) error {
	return ss.Set("last_channel", channel)
}

// GetLastChannel implements StateManagerInterface.
func (ss *StateStore) GetLastChannel() string {
	return ss.Get("last_channel")
}

// SetLastChatID implements StateManagerInterface.
func (ss *StateStore) SetLastChatID(chatID string) error {
	return ss.Set("last_chat_id", chatID)
}

// GetLastChatID implements StateManagerInterface.
func (ss *StateStore) GetLastChatID() string {
	return ss.Get("last_chat_id")
}

// GetTimestamp returns the timestamp of the last state update.
func (ss *StateStore) GetTimestamp() time.Time {
	var ts time.Time
	err := ss.db.QueryRow(
		"SELECT MAX(updated_at) FROM PICO_STATE WHERE agent_id = :1",
		ss.agentID,
	).Scan(&ts)
	if err != nil {
		return time.Time{}
	}
	return ts
}

// loadAll pre-populates the cache from Oracle at startup.
func (ss *StateStore) loadAll() {
	rows, err := ss.db.Query(
		"SELECT state_key, state_value FROM PICO_STATE WHERE agent_id = :1",
		ss.agentID,
	)
	if err != nil {
		logger.WarnCF("oracle", "Failed to load state", map[string]interface{}{"error": err.Error()})
		return
	}
	defer rows.Close()

	for rows.Next() {
		var key string
		var value sql.NullString
		if err := rows.Scan(&key, &value); err == nil && value.Valid {
			ss.cache[key] = value.String
		}
	}
}
