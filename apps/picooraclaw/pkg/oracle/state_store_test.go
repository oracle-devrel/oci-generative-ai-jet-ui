package oracle

import (
	"testing"

	"github.com/DATA-DOG/go-sqlmock"
)

func newMockStateStore(t *testing.T) (*StateStore, sqlmock.Sqlmock) {
	db, mock, err := sqlmock.New()
	if err != nil {
		t.Fatalf("failed to create sqlmock: %v", err)
	}

	// Expect loadAll query during construction
	mock.ExpectQuery("SELECT state_key, state_value FROM PICO_STATE").
		WithArgs("test-agent").
		WillReturnRows(sqlmock.NewRows([]string{"state_key", "state_value"}))

	store := NewStateStore(db, "test-agent")
	return store, mock
}

func TestStateStore_SetAndGet(t *testing.T) {
	store, mock := newMockStateStore(t)

	// Expect MERGE INTO for Set
	mock.ExpectExec("MERGE INTO PICO_STATE").
		WithArgs("last_channel", "test-agent", "telegram", "last_channel", "test-agent", "telegram").
		WillReturnResult(sqlmock.NewResult(0, 1))

	err := store.SetLastChannel("telegram")
	if err != nil {
		t.Fatalf("SetLastChannel failed: %v", err)
	}

	// Get should use cache (no DB query expected)
	channel := store.GetLastChannel()
	if channel != "telegram" {
		t.Errorf("GetLastChannel() = %q, want %q", channel, "telegram")
	}

	if err := mock.ExpectationsWereMet(); err != nil {
		t.Errorf("unfulfilled expectations: %v", err)
	}
}

func TestStateStore_SetLastChatID(t *testing.T) {
	store, mock := newMockStateStore(t)

	mock.ExpectExec("MERGE INTO PICO_STATE").
		WithArgs("last_chat_id", "test-agent", "chat-123", "last_chat_id", "test-agent", "chat-123").
		WillReturnResult(sqlmock.NewResult(0, 1))

	err := store.SetLastChatID("chat-123")
	if err != nil {
		t.Fatalf("SetLastChatID failed: %v", err)
	}

	chatID := store.GetLastChatID()
	if chatID != "chat-123" {
		t.Errorf("GetLastChatID() = %q, want %q", chatID, "chat-123")
	}

	if err := mock.ExpectationsWereMet(); err != nil {
		t.Errorf("unfulfilled expectations: %v", err)
	}
}

func TestStateStore_GetCacheMiss(t *testing.T) {
	store, mock := newMockStateStore(t)

	// Cache miss triggers DB query
	mock.ExpectQuery("SELECT state_value FROM PICO_STATE").
		WithArgs("unknown_key", "test-agent").
		WillReturnRows(sqlmock.NewRows([]string{"state_value"}))

	value := store.Get("unknown_key")
	if value != "" {
		t.Errorf("Get('unknown_key') = %q, want empty string", value)
	}

	if err := mock.ExpectationsWereMet(); err != nil {
		t.Errorf("unfulfilled expectations: %v", err)
	}
}

func TestStateStore_LoadAllPopulatesCache(t *testing.T) {
	db, mock, err := sqlmock.New()
	if err != nil {
		t.Fatalf("failed to create sqlmock: %v", err)
	}

	// loadAll returns pre-existing state
	rows := sqlmock.NewRows([]string{"state_key", "state_value"}).
		AddRow("last_channel", "discord").
		AddRow("last_chat_id", "chat-456")

	mock.ExpectQuery("SELECT state_key, state_value FROM PICO_STATE").
		WithArgs("test-agent").
		WillReturnRows(rows)

	store := NewStateStore(db, "test-agent")

	// Should be served from cache
	if ch := store.GetLastChannel(); ch != "discord" {
		t.Errorf("cached GetLastChannel() = %q, want %q", ch, "discord")
	}
	if id := store.GetLastChatID(); id != "chat-456" {
		t.Errorf("cached GetLastChatID() = %q, want %q", id, "chat-456")
	}

	if err := mock.ExpectationsWereMet(); err != nil {
		t.Errorf("unfulfilled expectations: %v", err)
	}
}
