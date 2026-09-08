package oracle

import (
	"testing"

	"github.com/DATA-DOG/go-sqlmock"
)

func TestMemoryStore_New(t *testing.T) {
	db, _, err := sqlmock.New()
	if err != nil {
		t.Fatalf("failed to create sqlmock: %v", err)
	}

	embSvc, err := NewEmbeddingService(db, "TEST_MODEL")
	if err != nil {
		t.Fatalf("NewEmbeddingService failed: %v", err)
	}
	store := NewMemoryStore(db, "test-agent", embSvc)

	if store == nil {
		t.Fatal("NewMemoryStore returned nil")
	}
}

func TestMemoryStore_ReadLongTermEmpty(t *testing.T) {
	db, mock, err := sqlmock.New()
	if err != nil {
		t.Fatalf("failed to create sqlmock: %v", err)
	}

	store := NewMemoryStore(db, "test-agent", nil)

	mock.ExpectQuery("SELECT content FROM PICO_MEMORIES").
		WithArgs("test-agent").
		WillReturnRows(sqlmock.NewRows([]string{"content"}))

	result := store.ReadLongTerm()
	if result != "" {
		t.Errorf("ReadLongTerm() with no memories should be empty, got %q", result)
	}

	if err := mock.ExpectationsWereMet(); err != nil {
		t.Errorf("unfulfilled expectations: %v", err)
	}
}

func TestMemoryStore_ReadLongTermWithData(t *testing.T) {
	db, mock, err := sqlmock.New()
	if err != nil {
		t.Fatalf("failed to create sqlmock: %v", err)
	}

	store := NewMemoryStore(db, "test-agent", nil)

	rows := sqlmock.NewRows([]string{"content"}).
		AddRow("Memory one").
		AddRow("Memory two")

	mock.ExpectQuery("SELECT content FROM PICO_MEMORIES").
		WithArgs("test-agent").
		WillReturnRows(rows)

	result := store.ReadLongTerm()
	expected := "Memory one\n\n---\n\nMemory two"
	if result != expected {
		t.Errorf("ReadLongTerm() = %q, want %q", result, expected)
	}

	if err := mock.ExpectationsWereMet(); err != nil {
		t.Errorf("unfulfilled expectations: %v", err)
	}
}

func TestMemoryStore_ReadTodayEmpty(t *testing.T) {
	db, mock, err := sqlmock.New()
	if err != nil {
		t.Fatalf("failed to create sqlmock: %v", err)
	}

	store := NewMemoryStore(db, "test-agent", nil)

	mock.ExpectQuery("SELECT content FROM PICO_DAILY_NOTES").
		WithArgs("test-agent").
		WillReturnRows(sqlmock.NewRows([]string{"content"}))

	result := store.ReadToday()
	if result != "" {
		t.Errorf("ReadToday() with no notes should be empty, got %q", result)
	}

	if err := mock.ExpectationsWereMet(); err != nil {
		t.Errorf("unfulfilled expectations: %v", err)
	}
}

func TestMemoryStore_Remember(t *testing.T) {
	db, mock, err := sqlmock.New(sqlmock.QueryMatcherOption(sqlmock.QueryMatcherRegexp))
	if err != nil {
		t.Fatalf("failed to create sqlmock: %v", err)
	}

	// No embedding service - stores without vector
	store := NewMemoryStore(db, "test-agent", nil)

	mock.ExpectExec("INSERT INTO PICO_MEMORIES").
		WithArgs(sqlmock.AnyArg(), "test-agent", "My favorite color is blue", 0.8, "preference").
		WillReturnResult(sqlmock.NewResult(0, 1))

	memID, err := store.Remember("My favorite color is blue", 0.8, "preference")
	if err != nil {
		t.Fatalf("Remember failed: %v", err)
	}
	if memID == "" {
		t.Error("Remember returned empty memory ID")
	}
	if len(memID) != 8 {
		t.Errorf("memory ID length = %d, want 8", len(memID))
	}

	if err := mock.ExpectationsWereMet(); err != nil {
		t.Errorf("unfulfilled expectations: %v", err)
	}
}

func TestMemoryStore_Forget(t *testing.T) {
	db, mock, err := sqlmock.New()
	if err != nil {
		t.Fatalf("failed to create sqlmock: %v", err)
	}

	store := NewMemoryStore(db, "test-agent", nil)

	// Successful delete
	mock.ExpectExec("DELETE FROM PICO_MEMORIES").
		WithArgs("mem-123", "test-agent").
		WillReturnResult(sqlmock.NewResult(0, 1))

	err = store.Forget("mem-123")
	if err != nil {
		t.Fatalf("Forget failed: %v", err)
	}

	// Memory not found
	mock.ExpectExec("DELETE FROM PICO_MEMORIES").
		WithArgs("nonexistent", "test-agent").
		WillReturnResult(sqlmock.NewResult(0, 0))

	err = store.Forget("nonexistent")
	if err == nil {
		t.Error("Forget should fail for nonexistent memory")
	}

	if err := mock.ExpectationsWereMet(); err != nil {
		t.Errorf("unfulfilled expectations: %v", err)
	}
}

func TestMemoryStore_RecallNoEmbedding(t *testing.T) {
	db, _, err := sqlmock.New()
	if err != nil {
		t.Fatalf("failed to create sqlmock: %v", err)
	}

	// No embedding service
	store := NewMemoryStore(db, "test-agent", nil)

	_, err = store.Recall("test query", 5)
	if err == nil {
		t.Error("Recall should fail without embedding service")
	}
}

func TestMemoryStore_WriteLongTermDelegatesToRemember(t *testing.T) {
	db, mock, err := sqlmock.New(sqlmock.QueryMatcherOption(sqlmock.QueryMatcherRegexp))
	if err != nil {
		t.Fatalf("failed to create sqlmock: %v", err)
	}

	store := NewMemoryStore(db, "test-agent", nil)

	mock.ExpectExec("INSERT INTO PICO_MEMORIES").
		WithArgs(sqlmock.AnyArg(), "test-agent", "Important fact", 0.7, "long_term").
		WillReturnResult(sqlmock.NewResult(0, 1))

	err = store.WriteLongTerm("Important fact")
	if err != nil {
		t.Fatalf("WriteLongTerm failed: %v", err)
	}

	if err := mock.ExpectationsWereMet(); err != nil {
		t.Errorf("unfulfilled expectations: %v", err)
	}
}

func TestMemoryStore_GetMemoryContextEmpty(t *testing.T) {
	db, mock, err := sqlmock.New()
	if err != nil {
		t.Fatalf("failed to create sqlmock: %v", err)
	}

	store := NewMemoryStore(db, "test-agent", nil)

	// ReadLongTerm returns empty
	mock.ExpectQuery("SELECT content FROM PICO_MEMORIES").
		WithArgs("test-agent").
		WillReturnRows(sqlmock.NewRows([]string{"content"}))

	// GetRecentDailyNotes returns empty
	mock.ExpectQuery("SELECT content FROM PICO_DAILY_NOTES").
		WithArgs("test-agent", 3).
		WillReturnRows(sqlmock.NewRows([]string{"content"}))

	result := store.GetMemoryContext()
	if result != "" {
		t.Errorf("GetMemoryContext() should be empty when no data, got %q", result)
	}

	if err := mock.ExpectationsWereMet(); err != nil {
		t.Errorf("unfulfilled expectations: %v", err)
	}
}

func TestMemoryStore_GetMemoryContextWithData(t *testing.T) {
	db, mock, err := sqlmock.New()
	if err != nil {
		t.Fatalf("failed to create sqlmock: %v", err)
	}

	store := NewMemoryStore(db, "test-agent", nil)

	// ReadLongTerm
	mock.ExpectQuery("SELECT content FROM PICO_MEMORIES").
		WithArgs("test-agent").
		WillReturnRows(sqlmock.NewRows([]string{"content"}).AddRow("I like Go"))

	// GetRecentDailyNotes
	mock.ExpectQuery("SELECT content FROM PICO_DAILY_NOTES").
		WithArgs("test-agent", 3).
		WillReturnRows(sqlmock.NewRows([]string{"content"}).AddRow("Today I coded"))

	result := store.GetMemoryContext()
	if result == "" {
		t.Error("GetMemoryContext() should not be empty with data")
	}
	if len(result) < 20 {
		t.Errorf("GetMemoryContext() too short: %q", result)
	}

	if err := mock.ExpectationsWereMet(); err != nil {
		t.Errorf("unfulfilled expectations: %v", err)
	}
}
