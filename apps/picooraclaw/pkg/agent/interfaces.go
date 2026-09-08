package agent

import "github.com/jasperan/picooraclaw/pkg/providers"

// MemoryStoreInterface defines the contract for memory storage backends.
// Both file-based (MemoryStore) and Oracle-backed implementations satisfy this.
type MemoryStoreInterface interface {
	ReadLongTerm() string
	WriteLongTerm(content string) error
	ReadToday() string
	AppendToday(content string) error
	GetRecentDailyNotes(days int) string
	GetMemoryContext() string
}

// SessionManagerInterface defines the contract for session management backends.
type SessionManagerInterface interface {
	AddMessage(key, role, content string)
	AddFullMessage(key string, msg providers.Message)
	GetHistory(key string) []providers.Message
	SetHistory(key string, history []providers.Message)
	GetSummary(key string) string
	SetSummary(key, summary string)
	TruncateHistory(key string, keepLast int)
	Save(key string) error
}

// StateManagerInterface defines the contract for state management backends.
type StateManagerInterface interface {
	SetLastChannel(channel string) error
	GetLastChannel() string
	SetLastChatID(chatID string) error
	GetLastChatID() string
}

// OracleMemoryStore is an extended interface for Oracle-backed memory with vector search.
type OracleMemoryStore interface {
	MemoryStoreInterface
	Remember(text string, importance float64, category string) (string, error)
	Recall(query string, maxResults int) ([]MemoryRecallResult, error)
	Forget(memoryID string) error
}

// MemoryRecallResult represents a single recalled memory with similarity score.
type MemoryRecallResult struct {
	MemoryID   string  `json:"memory_id"`
	Text       string  `json:"text"`
	Importance float64 `json:"importance"`
	Category   string  `json:"category"`
	Score      float64 `json:"score"`
}
