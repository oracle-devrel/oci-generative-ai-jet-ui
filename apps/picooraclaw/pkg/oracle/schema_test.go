package oracle

import (
	"fmt"
	"testing"

	"github.com/DATA-DOG/go-sqlmock"
)

func TestInitSchema_CreatesAllTables(t *testing.T) {
	db, mock, err := sqlmock.New()
	if err != nil {
		t.Fatalf("failed to create sqlmock: %v", err)
	}

	expectedTables := []string{
		"PICO_META", "PICO_MEMORIES", "PICO_DAILY_NOTES", "PICO_SESSIONS",
		"PICO_STATE", "PICO_CONFIG", "PICO_PROMPTS", "PICO_TRANSCRIPTS",
	}

	// Expect CREATE TABLE for each
	for range expectedTables {
		mock.ExpectExec("CREATE TABLE").
			WillReturnResult(sqlmock.NewResult(0, 0))
	}

	// Expect regular indexes (5)
	for range indexDDL {
		mock.ExpectExec("CREATE INDEX").
			WillReturnResult(sqlmock.NewResult(0, 0))
	}

	// Expect vector indexes (2)
	for range vectorIndexDDL {
		mock.ExpectExec("CREATE VECTOR INDEX").
			WillReturnResult(sqlmock.NewResult(0, 0))
	}

	// Expect schema version MERGE
	mock.ExpectExec("MERGE INTO PICO_META").
		WillReturnResult(sqlmock.NewResult(0, 1))

	err = InitSchema(db)
	if err != nil {
		t.Fatalf("InitSchema failed: %v", err)
	}

	if err := mock.ExpectationsWereMet(); err != nil {
		t.Errorf("unfulfilled expectations: %v", err)
	}
}

func TestInitSchema_Idempotent(t *testing.T) {
	db, mock, err := sqlmock.New()
	if err != nil {
		t.Fatalf("failed to create sqlmock: %v", err)
	}

	// Simulate all tables already existing (ORA-00955)
	for i := 0; i < 8; i++ {
		mock.ExpectExec("CREATE TABLE").
			WillReturnError(fmt.Errorf("ORA-00955: name is already used by an existing object"))
	}

	// Indexes already exist (ORA-01408)
	for range indexDDL {
		mock.ExpectExec("CREATE INDEX").
			WillReturnError(fmt.Errorf("ORA-01408: such column list already indexed"))
	}

	for range vectorIndexDDL {
		mock.ExpectExec("CREATE VECTOR INDEX").
			WillReturnError(fmt.Errorf("ORA-00955: name is already used by an existing object"))
	}

	// Schema version still runs
	mock.ExpectExec("MERGE INTO PICO_META").
		WillReturnResult(sqlmock.NewResult(0, 1))

	err = InitSchema(db)
	if err != nil {
		t.Fatalf("idempotent InitSchema should not fail: %v", err)
	}

	if err := mock.ExpectationsWereMet(); err != nil {
		t.Errorf("unfulfilled expectations: %v", err)
	}
}

func TestIsORA00955(t *testing.T) {
	if !isORA00955(fmt.Errorf("ORA-00955: name is already used")) {
		t.Error("should detect ORA-00955")
	}
	if isORA00955(fmt.Errorf("ORA-01408: column list already indexed")) {
		t.Error("should not match ORA-01408")
	}
}

func TestIsORA01408(t *testing.T) {
	if !isORA01408(fmt.Errorf("ORA-01408: such column list already indexed")) {
		t.Error("should detect ORA-01408")
	}
	if isORA01408(fmt.Errorf("ORA-00955: name already used")) {
		t.Error("should not match ORA-00955")
	}
}

func TestTableDDL_AllTablesHavePICOPrefix(t *testing.T) {
	for name := range tableDDL {
		if name[:5] != "PICO_" {
			t.Errorf("table %q does not have PICO_ prefix", name)
		}
	}
}

func TestTableDDL_ExpectedTableCount(t *testing.T) {
	if len(tableDDL) != 8 {
		t.Errorf("expected 8 tables, got %d", len(tableDDL))
	}
}
