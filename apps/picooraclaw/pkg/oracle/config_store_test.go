package oracle

import (
	"testing"

	"github.com/DATA-DOG/go-sqlmock"
)

func TestConfigStore_GetSetValue(t *testing.T) {
	db, mock, err := sqlmock.New()
	if err != nil {
		t.Fatalf("failed to create sqlmock: %v", err)
	}

	store := NewConfigStore(db, "test-agent")

	// Set a value
	mock.ExpectExec("MERGE INTO PICO_CONFIG").
		WillReturnResult(sqlmock.NewResult(0, 1))

	err = store.SetConfigValue("theme", "dark")
	if err != nil {
		t.Fatalf("SetConfigValue failed: %v", err)
	}

	// Get the value
	mock.ExpectQuery("SELECT config_value FROM PICO_CONFIG").
		WithArgs("theme", "test-agent").
		WillReturnRows(sqlmock.NewRows([]string{"config_value"}).AddRow("dark"))

	val, err := store.GetConfigValue("theme")
	if err != nil {
		t.Fatalf("GetConfigValue failed: %v", err)
	}
	if val != "dark" {
		t.Errorf("GetConfigValue('theme') = %q, want %q", val, "dark")
	}

	if err := mock.ExpectationsWereMet(); err != nil {
		t.Errorf("unfulfilled expectations: %v", err)
	}
}

func TestConfigStore_GetMissing(t *testing.T) {
	db, mock, err := sqlmock.New()
	if err != nil {
		t.Fatalf("failed to create sqlmock: %v", err)
	}

	store := NewConfigStore(db, "test-agent")

	mock.ExpectQuery("SELECT config_value FROM PICO_CONFIG").
		WithArgs("nonexistent", "test-agent").
		WillReturnRows(sqlmock.NewRows([]string{"config_value"}))

	val, err := store.GetConfigValue("nonexistent")
	if err != nil {
		t.Fatalf("GetConfigValue should not error for missing key, got: %v", err)
	}
	if val != "" {
		t.Errorf("expected empty string for missing key, got %q", val)
	}

	if err := mock.ExpectationsWereMet(); err != nil {
		t.Errorf("unfulfilled expectations: %v", err)
	}
}

func TestConfigStore_LoadSaveConfig(t *testing.T) {
	db, mock, err := sqlmock.New()
	if err != nil {
		t.Fatalf("failed to create sqlmock: %v", err)
	}

	store := NewConfigStore(db, "test-agent")

	configJSON := `{"model": "gpt-4", "temperature": 0.7}`

	// SaveConfig -> SetConfigValue("full_config", ...)
	mock.ExpectExec("MERGE INTO PICO_CONFIG").
		WillReturnResult(sqlmock.NewResult(0, 1))

	err = store.SaveConfig(configJSON)
	if err != nil {
		t.Fatalf("SaveConfig failed: %v", err)
	}

	// LoadConfig -> GetConfigValue("full_config")
	mock.ExpectQuery("SELECT config_value FROM PICO_CONFIG").
		WithArgs("full_config", "test-agent").
		WillReturnRows(sqlmock.NewRows([]string{"config_value"}).AddRow(configJSON))

	loaded, err := store.LoadConfig()
	if err != nil {
		t.Fatalf("LoadConfig failed: %v", err)
	}
	if loaded != configJSON {
		t.Errorf("LoadConfig() = %q, want %q", loaded, configJSON)
	}

	if err := mock.ExpectationsWereMet(); err != nil {
		t.Errorf("unfulfilled expectations: %v", err)
	}
}
