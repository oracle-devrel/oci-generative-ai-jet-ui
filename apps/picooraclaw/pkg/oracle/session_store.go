package oracle

import (
	"database/sql"
	"encoding/json"
	"fmt"
	"sync"
	"time"

	"github.com/jasperan/picooraclaw/pkg/logger"
	"github.com/jasperan/picooraclaw/pkg/providers"
)

// OracleSession mirrors the file-based Session struct.
type OracleSession struct {
	Key      string              `json:"key"`
	Messages []providers.Message `json:"messages"`
	Summary  string              `json:"summary,omitempty"`
	Created  time.Time           `json:"created"`
	Updated  time.Time           `json:"updated"`
}

// SessionStore implements SessionManagerInterface backed by Oracle.
type SessionStore struct {
	db       *sql.DB
	agentID  string
	sessions map[string]*OracleSession
	mu       sync.RWMutex
}

// NewSessionStore creates a new Oracle-backed session store.
func NewSessionStore(db *sql.DB, agentID string) *SessionStore {
	ss := &SessionStore{
		db:       db,
		agentID:  agentID,
		sessions: make(map[string]*OracleSession),
	}
	ss.loadAll()
	return ss
}

// GetOrCreate returns an existing session or creates a new one.
func (ss *SessionStore) GetOrCreate(key string) interface{} {
	ss.mu.Lock()
	defer ss.mu.Unlock()

	if s, ok := ss.sessions[key]; ok {
		return s
	}

	s := &OracleSession{
		Key:      key,
		Messages: []providers.Message{},
		Created:  time.Now(),
		Updated:  time.Now(),
	}
	ss.sessions[key] = s
	return s
}

// AddMessage adds a simple role/content message to the session.
func (ss *SessionStore) AddMessage(key, role, content string) {
	ss.AddFullMessage(key, providers.Message{
		Role:    role,
		Content: content,
	})
}

// AddFullMessage adds a complete message with tool calls.
func (ss *SessionStore) AddFullMessage(key string, msg providers.Message) {
	ss.mu.Lock()
	defer ss.mu.Unlock()

	s, ok := ss.sessions[key]
	if !ok {
		s = &OracleSession{
			Key:      key,
			Messages: []providers.Message{},
			Created:  time.Now(),
		}
		ss.sessions[key] = s
	}

	s.Messages = append(s.Messages, msg)
	s.Updated = time.Now()
}

// GetHistory returns a copy of the session's message history.
func (ss *SessionStore) GetHistory(key string) []providers.Message {
	ss.mu.RLock()
	defer ss.mu.RUnlock()

	s, ok := ss.sessions[key]
	if !ok {
		return []providers.Message{}
	}

	history := make([]providers.Message, len(s.Messages))
	copy(history, s.Messages)
	return history
}

// GetSummary returns the session summary.
func (ss *SessionStore) GetSummary(key string) string {
	ss.mu.RLock()
	defer ss.mu.RUnlock()

	s, ok := ss.sessions[key]
	if !ok {
		return ""
	}
	return s.Summary
}

// SetSummary updates the session summary.
func (ss *SessionStore) SetSummary(key, summary string) {
	ss.mu.Lock()
	defer ss.mu.Unlock()

	if s, ok := ss.sessions[key]; ok {
		s.Summary = summary
		s.Updated = time.Now()
	}
}

// TruncateHistory keeps only the last N messages.
func (ss *SessionStore) TruncateHistory(key string, keepLast int) {
	ss.mu.Lock()
	defer ss.mu.Unlock()

	s, ok := ss.sessions[key]
	if !ok {
		return
	}

	if keepLast <= 0 {
		s.Messages = []providers.Message{}
	} else if len(s.Messages) > keepLast {
		s.Messages = s.Messages[len(s.Messages)-keepLast:]
	}
	s.Updated = time.Now()
}

// SetHistory replaces the session's full message history.
func (ss *SessionStore) SetHistory(key string, history []providers.Message) {
	ss.mu.Lock()
	defer ss.mu.Unlock()

	s, ok := ss.sessions[key]
	if !ok {
		return
	}

	msgs := make([]providers.Message, len(history))
	copy(msgs, history)
	s.Messages = msgs
	s.Updated = time.Now()
}

// Save persists the session to Oracle using MERGE INTO.
func (ss *SessionStore) Save(key string) error {
	ss.mu.RLock()
	s, ok := ss.sessions[key]
	if !ok {
		ss.mu.RUnlock()
		return nil
	}

	// Snapshot under lock
	messagesJSON, err := json.Marshal(s.Messages)
	if err != nil {
		ss.mu.RUnlock()
		return fmt.Errorf("failed to marshal messages: %w", err)
	}
	summary := s.Summary
	ss.mu.RUnlock()

	_, err = ss.db.Exec(`
		MERGE INTO PICO_SESSIONS s
		USING (SELECT :1 AS session_key FROM DUAL) src
		ON (s.session_key = src.session_key)
		WHEN MATCHED THEN
			UPDATE SET messages = :2, summary = :3, updated_at = CURRENT_TIMESTAMP
		WHEN NOT MATCHED THEN
			INSERT (session_key, agent_id, messages, summary)
			VALUES (:4, :5, :6, :7)
	`, key, string(messagesJSON), summary, key, ss.agentID, string(messagesJSON), summary)

	if err != nil {
		return fmt.Errorf("session save failed: %w", err)
	}
	return nil
}

// loadAll loads all sessions from Oracle into the cache.
func (ss *SessionStore) loadAll() {
	rows, err := ss.db.Query(
		"SELECT session_key, messages, summary, created_at, updated_at FROM PICO_SESSIONS WHERE agent_id = :1",
		ss.agentID,
	)
	if err != nil {
		logger.WarnCF("oracle", "Failed to load sessions", map[string]interface{}{"error": err.Error()})
		return
	}
	defer rows.Close()

	count := 0
	for rows.Next() {
		var key string
		var messagesStr sql.NullString
		var summaryStr sql.NullString
		var created, updated time.Time

		if err := rows.Scan(&key, &messagesStr, &summaryStr, &created, &updated); err != nil {
			continue
		}

		s := &OracleSession{
			Key:     key,
			Created: created,
			Updated: updated,
		}

		if messagesStr.Valid && messagesStr.String != "" {
			var msgs []providers.Message
			if err := json.Unmarshal([]byte(messagesStr.String), &msgs); err == nil {
				s.Messages = msgs
			} else {
				s.Messages = []providers.Message{}
			}
		} else {
			s.Messages = []providers.Message{}
		}

		if summaryStr.Valid {
			s.Summary = summaryStr.String
		}

		ss.sessions[key] = s
		count++
	}

	if count > 0 {
		logger.InfoCF("oracle", "Loaded sessions from Oracle", map[string]interface{}{"count": count})
	}
}
