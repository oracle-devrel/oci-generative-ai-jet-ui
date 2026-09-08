package oracle

import (
	"testing"

	"github.com/DATA-DOG/go-sqlmock"
	"github.com/jasperan/picooraclaw/pkg/providers"
)

func newMockSessionStore(t *testing.T) (*SessionStore, sqlmock.Sqlmock) {
	db, mock, err := sqlmock.New()
	if err != nil {
		t.Fatalf("failed to create sqlmock: %v", err)
	}

	// loadAll during construction
	mock.ExpectQuery("SELECT session_key, messages, summary, created_at, updated_at FROM PICO_SESSIONS").
		WithArgs("test-agent").
		WillReturnRows(sqlmock.NewRows([]string{"session_key", "messages", "summary", "created_at", "updated_at"}))

	store := NewSessionStore(db, "test-agent")
	return store, mock
}

func TestSessionStore_GetOrCreate(t *testing.T) {
	store, mock := newMockSessionStore(t)

	s := store.GetOrCreate("test-session")
	if s == nil {
		t.Fatal("GetOrCreate returned nil")
	}

	session, ok := s.(*OracleSession)
	if !ok {
		t.Fatal("GetOrCreate did not return *OracleSession")
	}

	if session.Key != "test-session" {
		t.Errorf("session.Key = %q, want %q", session.Key, "test-session")
	}
	if len(session.Messages) != 0 {
		t.Errorf("new session should have 0 messages, got %d", len(session.Messages))
	}

	// Getting same key returns same session
	s2 := store.GetOrCreate("test-session")
	if s2 != s {
		t.Error("GetOrCreate should return same session for same key")
	}

	if err := mock.ExpectationsWereMet(); err != nil {
		t.Errorf("unfulfilled expectations: %v", err)
	}
}

func TestSessionStore_AddMessage(t *testing.T) {
	store, mock := newMockSessionStore(t)

	store.AddMessage("sess1", "user", "Hello")
	store.AddMessage("sess1", "assistant", "Hi there!")

	history := store.GetHistory("sess1")
	if len(history) != 2 {
		t.Fatalf("expected 2 messages, got %d", len(history))
	}

	if history[0].Role != "user" || history[0].Content != "Hello" {
		t.Errorf("first message = {%s, %s}, want {user, Hello}", history[0].Role, history[0].Content)
	}
	if history[1].Role != "assistant" || history[1].Content != "Hi there!" {
		t.Errorf("second message = {%s, %s}, want {assistant, Hi there!}", history[1].Role, history[1].Content)
	}

	if err := mock.ExpectationsWereMet(); err != nil {
		t.Errorf("unfulfilled expectations: %v", err)
	}
}

func TestSessionStore_AddFullMessage(t *testing.T) {
	store, mock := newMockSessionStore(t)

	msg := providers.Message{
		Role:    "assistant",
		Content: "Here's the result",
	}

	store.AddFullMessage("sess1", msg)

	history := store.GetHistory("sess1")
	if len(history) != 1 {
		t.Fatalf("expected 1 message, got %d", len(history))
	}
	if history[0].Content != "Here's the result" {
		t.Errorf("message content = %q, want %q", history[0].Content, "Here's the result")
	}

	if err := mock.ExpectationsWereMet(); err != nil {
		t.Errorf("unfulfilled expectations: %v", err)
	}
}

func TestSessionStore_Summary(t *testing.T) {
	store, mock := newMockSessionStore(t)

	// Initially empty
	if s := store.GetSummary("sess1"); s != "" {
		t.Errorf("initial summary should be empty, got %q", s)
	}

	// Need to create session first
	store.GetOrCreate("sess1")
	store.SetSummary("sess1", "User asked about Go programming")

	summary := store.GetSummary("sess1")
	if summary != "User asked about Go programming" {
		t.Errorf("summary = %q, want %q", summary, "User asked about Go programming")
	}

	if err := mock.ExpectationsWereMet(); err != nil {
		t.Errorf("unfulfilled expectations: %v", err)
	}
}

func TestSessionStore_TruncateHistory(t *testing.T) {
	store, mock := newMockSessionStore(t)

	// Add 5 messages
	for i := 0; i < 5; i++ {
		store.AddMessage("sess1", "user", "msg")
		store.AddMessage("sess1", "assistant", "reply")
	}

	history := store.GetHistory("sess1")
	if len(history) != 10 {
		t.Fatalf("expected 10 messages before truncate, got %d", len(history))
	}

	// Keep last 4
	store.TruncateHistory("sess1", 4)

	history = store.GetHistory("sess1")
	if len(history) != 4 {
		t.Errorf("expected 4 messages after truncate, got %d", len(history))
	}

	if err := mock.ExpectationsWereMet(); err != nil {
		t.Errorf("unfulfilled expectations: %v", err)
	}
}

func TestSessionStore_Save(t *testing.T) {
	store, mock := newMockSessionStore(t)

	store.AddMessage("sess1", "user", "Hello")

	// Expect MERGE INTO for save
	mock.ExpectExec("MERGE INTO PICO_SESSIONS").
		WillReturnResult(sqlmock.NewResult(0, 1))

	err := store.Save("sess1")
	if err != nil {
		t.Fatalf("Save failed: %v", err)
	}

	if err := mock.ExpectationsWereMet(); err != nil {
		t.Errorf("unfulfilled expectations: %v", err)
	}
}

func TestSessionStore_GetHistoryEmpty(t *testing.T) {
	store, mock := newMockSessionStore(t)

	history := store.GetHistory("nonexistent")
	if len(history) != 0 {
		t.Errorf("expected empty history for nonexistent session, got %d", len(history))
	}

	if err := mock.ExpectationsWereMet(); err != nil {
		t.Errorf("unfulfilled expectations: %v", err)
	}
}

func TestSessionStore_HistoryIsCopy(t *testing.T) {
	store, mock := newMockSessionStore(t)

	store.AddMessage("sess1", "user", "Hello")

	h1 := store.GetHistory("sess1")
	h2 := store.GetHistory("sess1")

	// Modifying h1 should not affect h2
	h1[0].Content = "modified"
	if h2[0].Content == "modified" {
		t.Error("GetHistory should return a copy, not a reference")
	}

	if err := mock.ExpectationsWereMet(); err != nil {
		t.Errorf("unfulfilled expectations: %v", err)
	}
}
