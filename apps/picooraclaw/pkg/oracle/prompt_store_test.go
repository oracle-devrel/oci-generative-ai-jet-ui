package oracle

import (
	"os"
	"path/filepath"
	"testing"

	"github.com/DATA-DOG/go-sqlmock"
)

func TestPromptStore_LoadPrompt(t *testing.T) {
	db, mock, err := sqlmock.New()
	if err != nil {
		t.Fatalf("failed to create sqlmock: %v", err)
	}

	store := NewPromptStore(db, "test-agent")

	mock.ExpectQuery("SELECT content FROM PICO_PROMPTS").
		WithArgs("IDENTITY", "test-agent").
		WillReturnRows(sqlmock.NewRows([]string{"content"}).AddRow("You are a helpful AI assistant."))

	content, err := store.LoadPrompt("IDENTITY")
	if err != nil {
		t.Fatalf("LoadPrompt failed: %v", err)
	}
	if content != "You are a helpful AI assistant." {
		t.Errorf("LoadPrompt('IDENTITY') = %q", content)
	}

	if err := mock.ExpectationsWereMet(); err != nil {
		t.Errorf("unfulfilled expectations: %v", err)
	}
}

func TestPromptStore_LoadPromptMissing(t *testing.T) {
	db, mock, err := sqlmock.New()
	if err != nil {
		t.Fatalf("failed to create sqlmock: %v", err)
	}

	store := NewPromptStore(db, "test-agent")

	mock.ExpectQuery("SELECT content FROM PICO_PROMPTS").
		WithArgs("NONEXISTENT", "test-agent").
		WillReturnRows(sqlmock.NewRows([]string{"content"}))

	content, err := store.LoadPrompt("NONEXISTENT")
	if err != nil {
		t.Fatalf("LoadPrompt should not error for missing prompt, got: %v", err)
	}
	if content != "" {
		t.Errorf("expected empty for missing prompt, got %q", content)
	}

	if err := mock.ExpectationsWereMet(); err != nil {
		t.Errorf("unfulfilled expectations: %v", err)
	}
}

func TestPromptStore_SavePrompt(t *testing.T) {
	db, mock, err := sqlmock.New()
	if err != nil {
		t.Fatalf("failed to create sqlmock: %v", err)
	}

	store := NewPromptStore(db, "test-agent")

	mock.ExpectExec("MERGE INTO PICO_PROMPTS").
		WillReturnResult(sqlmock.NewResult(0, 1))

	err = store.SavePrompt("IDENTITY", "You are PicoOraClaw.")
	if err != nil {
		t.Fatalf("SavePrompt failed: %v", err)
	}

	if err := mock.ExpectationsWereMet(); err != nil {
		t.Errorf("unfulfilled expectations: %v", err)
	}
}

func TestPromptStore_LoadBootstrapFiles(t *testing.T) {
	db, mock, err := sqlmock.New()
	if err != nil {
		t.Fatalf("failed to create sqlmock: %v", err)
	}

	store := NewPromptStore(db, "test-agent")

	rows := sqlmock.NewRows([]string{"prompt_name", "content"}).
		AddRow("IDENTITY", "You are PicoOraClaw.").
		AddRow("SOUL", "Be helpful and kind.").
		AddRow("USER", "User preferences here.")

	mock.ExpectQuery("SELECT prompt_name, content FROM PICO_PROMPTS").
		WithArgs("test-agent").
		WillReturnRows(rows)

	result := store.LoadBootstrapFiles()
	if len(result) != 3 {
		t.Fatalf("expected 3 prompts, got %d", len(result))
	}
	if result["IDENTITY"] != "You are PicoOraClaw." {
		t.Errorf("IDENTITY = %q", result["IDENTITY"])
	}
	if result["SOUL"] != "Be helpful and kind." {
		t.Errorf("SOUL = %q", result["SOUL"])
	}

	if err := mock.ExpectationsWereMet(); err != nil {
		t.Errorf("unfulfilled expectations: %v", err)
	}
}

func TestPromptStore_SeedFromWorkspace(t *testing.T) {
	db, mock, err := sqlmock.New()
	if err != nil {
		t.Fatalf("failed to create sqlmock: %v", err)
	}

	store := NewPromptStore(db, "test-agent")

	// Create temp workspace
	tmpDir := t.TempDir()
	os.WriteFile(filepath.Join(tmpDir, "IDENTITY.md"), []byte("I am PicoOraClaw"), 0644)
	os.WriteFile(filepath.Join(tmpDir, "SOUL.md"), []byte("Be helpful"), 0644)

	// Expect two SavePrompt calls (MERGE INTO)
	mock.ExpectExec("MERGE INTO PICO_PROMPTS").
		WillReturnResult(sqlmock.NewResult(0, 1))
	mock.ExpectExec("MERGE INTO PICO_PROMPTS").
		WillReturnResult(sqlmock.NewResult(0, 1))

	err = store.SeedFromWorkspace(tmpDir)
	if err != nil {
		t.Fatalf("SeedFromWorkspace failed: %v", err)
	}

	if err := mock.ExpectationsWereMet(); err != nil {
		t.Errorf("unfulfilled expectations: %v", err)
	}
}
