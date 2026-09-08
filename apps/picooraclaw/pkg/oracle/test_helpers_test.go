package oracle

import (
	"database/sql"
	"testing"

	"github.com/DATA-DOG/go-sqlmock"
)

func newMockDB(t *testing.T) (*sql.DB, sqlmock.Sqlmock, error) {
	t.Helper()
	return sqlmock.New()
}

func mockEmptySessionRows() *sqlmock.Rows {
	return sqlmock.NewRows([]string{"session_key", "messages", "summary", "created_at", "updated_at"})
}

func mockEmptyStateRows() *sqlmock.Rows {
	return sqlmock.NewRows([]string{"state_key", "state_value"})
}
