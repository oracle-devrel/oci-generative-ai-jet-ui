package oracle

import (
	"database/sql"
	"fmt"
)

// VectorSearchResult represents a single result from a vector similarity search.
type VectorSearchResult struct {
	ID       string
	Text     string
	Distance float64
	Score    float64
}

// VectorSearch performs a generic vector similarity search on a table.
// It returns results ordered by cosine distance (ascending = most similar first).
func VectorSearch(db *sql.DB, table, idCol, textCol, embeddingCol, agentID string, queryVector []float32, maxResults int, minScore float64) ([]VectorSearchResult, error) {
	// Validate all SQL identifiers to prevent injection
	for name, val := range map[string]string{"table": table, "idCol": idCol, "textCol": textCol, "embeddingCol": embeddingCol} {
		if err := validateSQLIdentifier(val); err != nil {
			return nil, fmt.Errorf("invalid %s: %w", name, err)
		}
	}

	query := fmt.Sprintf(`
		SELECT %s, %s,
		       VECTOR_DISTANCE(%s, :1, COSINE) AS distance
		FROM %s
		WHERE agent_id = :2
		  AND %s IS NOT NULL
		ORDER BY distance ASC
		FETCH FIRST :3 ROWS ONLY`,
		idCol, textCol, embeddingCol, table, embeddingCol,
	)

	rows, err := db.Query(query, queryVector, agentID, maxResults)
	if err != nil {
		return nil, fmt.Errorf("vector search failed on %s: %w", table, err)
	}
	defer rows.Close()

	var results []VectorSearchResult
	for rows.Next() {
		var r VectorSearchResult
		var textVal sql.NullString
		if err := rows.Scan(&r.ID, &textVal, &r.Distance); err != nil {
			return nil, fmt.Errorf("scan failed: %w", err)
		}
		if textVal.Valid {
			r.Text = textVal.String
		}
		r.Score = 1.0 - r.Distance // Convert cosine distance to similarity
		if r.Score < minScore {
			continue
		}
		results = append(results, r)
	}

	return results, rows.Err()
}
