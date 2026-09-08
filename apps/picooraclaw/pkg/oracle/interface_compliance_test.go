package oracle

import (
	"testing"

	"github.com/jasperan/picooraclaw/pkg/agent"
)

// These tests verify at compile time that Oracle stores implement the agent interfaces.
// If any method signature doesn't match, the build will fail.

func TestSessionStore_ImplementsInterface(t *testing.T) {
	db, mock, _ := newMockDB(t)
	mock.ExpectQuery("SELECT session_key").
		WillReturnRows(mockEmptySessionRows())

	var _ agent.SessionManagerInterface = NewSessionStore(db, "test")
}

func TestStateStore_ImplementsInterface(t *testing.T) {
	db, mock, _ := newMockDB(t)
	mock.ExpectQuery("SELECT state_key").
		WillReturnRows(mockEmptyStateRows())

	var _ agent.StateManagerInterface = NewStateStore(db, "test")
}

func TestMemoryStore_ImplementsInterface(t *testing.T) {
	db, _, _ := newMockDB(t)
	var _ agent.MemoryStoreInterface = NewMemoryStore(db, "test", nil)
}

func TestPromptStore_ImplementsPromptStoreInterface(t *testing.T) {
	db, _, _ := newMockDB(t)
	var _ agent.PromptStoreInterface = NewPromptStore(db, "test")
}
