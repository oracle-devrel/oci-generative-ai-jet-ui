package oracle

import "fmt"

// validateSQLIdentifier checks that a string is a safe SQL identifier (alphanumeric + underscore only).
func validateSQLIdentifier(s string) error {
	if s == "" {
		return fmt.Errorf("empty SQL identifier")
	}
	for i, r := range s {
		if r == '_' || (r >= 'A' && r <= 'Z') || (r >= 'a' && r <= 'z') || (i > 0 && r >= '0' && r <= '9') {
			continue
		}
		return fmt.Errorf("invalid character %q in SQL identifier %q", r, s)
	}
	return nil
}
