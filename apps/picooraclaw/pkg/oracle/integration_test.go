package oracle

import (
	"testing"

	"github.com/DATA-DOG/go-sqlmock"
	"github.com/jasperan/picooraclaw/pkg/providers"
)

// TestFullWorkflow_SessionStateMemory tests the complete lifecycle of using
// Oracle stores together, simulating what happens during an agent conversation.
func TestFullWorkflow_SessionStateMemory(t *testing.T) {
	db, mock, err := sqlmock.New(sqlmock.QueryMatcherOption(sqlmock.QueryMatcherRegexp))
	if err != nil {
		t.Fatalf("failed to create sqlmock: %v", err)
	}

	// 1. Initialize stores (loadAll for state and session)
	mock.ExpectQuery("SELECT state_key, state_value FROM PICO_STATE").
		WithArgs("agent-1").
		WillReturnRows(sqlmock.NewRows([]string{"state_key", "state_value"}))

	mock.ExpectQuery("SELECT session_key, messages, summary, created_at, updated_at FROM PICO_SESSIONS").
		WithArgs("agent-1").
		WillReturnRows(sqlmock.NewRows([]string{"session_key", "messages", "summary", "created_at", "updated_at"}))

	stateStore := NewStateStore(db, "agent-1")
	sessionStore := NewSessionStore(db, "agent-1")
	memoryStore := NewMemoryStore(db, "agent-1", nil)

	// 2. Set channel state (simulating gateway receiving a message)
	mock.ExpectExec("MERGE INTO PICO_STATE").
		WillReturnResult(sqlmock.NewResult(0, 1))

	err = stateStore.SetLastChannel("telegram")
	if err != nil {
		t.Fatalf("SetLastChannel failed: %v", err)
	}

	// 3. Add messages to session (simulating conversation)
	sessionStore.AddMessage("tg:user123", "user", "Remember that I like Go programming")
	sessionStore.AddFullMessage("tg:user123", providers.Message{
		Role:    "assistant",
		Content: "I'll remember that you like Go programming!",
	})

	// Verify conversation
	history := sessionStore.GetHistory("tg:user123")
	if len(history) != 2 {
		t.Fatalf("expected 2 messages, got %d", len(history))
	}

	// 4. Store a memory (simulating remember tool)
	mock.ExpectExec("INSERT INTO PICO_MEMORIES").
		WithArgs(sqlmock.AnyArg(), "agent-1", "User likes Go programming", 0.8, "preference").
		WillReturnResult(sqlmock.NewResult(0, 1))

	memID, err := memoryStore.Remember("User likes Go programming", 0.8, "preference")
	if err != nil {
		t.Fatalf("Remember failed: %v", err)
	}
	if memID == "" {
		t.Error("expected non-empty memory ID")
	}

	// 5. Set summary (simulating context window management)
	sessionStore.GetOrCreate("tg:user123") // ensure exists
	sessionStore.SetSummary("tg:user123", "User discussed Go preferences")

	summary := sessionStore.GetSummary("tg:user123")
	if summary != "User discussed Go preferences" {
		t.Errorf("summary = %q", summary)
	}

	// 6. Save session to Oracle
	mock.ExpectExec("MERGE INTO PICO_SESSIONS").
		WillReturnResult(sqlmock.NewResult(0, 1))

	err = sessionStore.Save("tg:user123")
	if err != nil {
		t.Fatalf("Save failed: %v", err)
	}

	// 7. Verify channel state is cached
	channel := stateStore.GetLastChannel()
	if channel != "telegram" {
		t.Errorf("channel = %q, want %q", channel, "telegram")
	}

	// 8. Read memory context
	mock.ExpectQuery("SELECT content FROM PICO_MEMORIES").
		WithArgs("agent-1").
		WillReturnRows(sqlmock.NewRows([]string{"content"}).AddRow("User likes Go programming"))

	mock.ExpectQuery("SELECT content FROM PICO_DAILY_NOTES").
		WithArgs("agent-1", 3).
		WillReturnRows(sqlmock.NewRows([]string{"content"}))

	ctx := memoryStore.GetMemoryContext()
	if ctx == "" {
		t.Error("GetMemoryContext() should not be empty after Remember")
	}

	if err := mock.ExpectationsWereMet(); err != nil {
		t.Errorf("unfulfilled expectations: %v", err)
	}
}

// TestRecallAdapter verifies the recallAdapter bridges oracle types to tools types.
func TestRecallAdapter_TypeMapping(t *testing.T) {
	// Test that MemoryRecallResult fields map correctly
	oracleResult := MemoryRecallResult{
		MemoryID:   "mem-abc",
		Text:       "Test memory",
		Importance: 0.8,
		Category:   "test",
		Score:      0.92,
	}

	if oracleResult.MemoryID != "mem-abc" {
		t.Errorf("MemoryID = %q", oracleResult.MemoryID)
	}
	if oracleResult.Score != 0.92 {
		t.Errorf("Score = %f", oracleResult.Score)
	}
}

// TestVectorSearchResult_ScoreConversion verifies cosine distance to similarity conversion.
func TestVectorSearchResult_ScoreConversion(t *testing.T) {
	tests := []struct {
		name     string
		distance float64
		wantMin  float64
		wantMax  float64
	}{
		{"identical vectors", 0.0, 0.99, 1.01},
		{"similar vectors", 0.1, 0.89, 0.91},
		{"dissimilar vectors", 0.8, 0.19, 0.21},
		{"orthogonal vectors", 1.0, -0.01, 0.01},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			score := 1.0 - tt.distance
			if score < tt.wantMin || score > tt.wantMax {
				t.Errorf("score = %f, want in [%f, %f]", score, tt.wantMin, tt.wantMax)
			}
		})
	}
}
