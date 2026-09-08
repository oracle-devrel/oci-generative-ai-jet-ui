package oracle

import (
	"database/sql"
	"fmt"
	"strings"
	"time"

	"github.com/google/uuid"
	"github.com/jasperan/picooraclaw/pkg/logger"
)

// MemoryRecallResult represents a single recalled memory with similarity score.
type MemoryRecallResult struct {
	MemoryID   string  `json:"memory_id"`
	Text       string  `json:"text"`
	Importance float64 `json:"importance"`
	Category   string  `json:"category"`
	Score      float64 `json:"score"`
}

// MemoryStore implements MemoryStoreInterface and OracleMemoryStore backed by Oracle.
type MemoryStore struct {
	db        *sql.DB
	agentID   string
	embedding *EmbeddingService
	modelName string // ONNX model name for VECTOR_EMBEDDING() SQL
}

// NewMemoryStore creates a new Oracle-backed memory store.
func NewMemoryStore(db *sql.DB, agentID string, embedding *EmbeddingService) *MemoryStore {
	modelName := ""
	if embedding != nil {
		modelName = embedding.ModelName()
	}
	if modelName != "" {
		if err := validateSQLIdentifier(modelName); err != nil {
			logger.WarnCF("oracle", "Invalid model name for MemoryStore, disabling embedding SQL", map[string]interface{}{"error": err.Error(), "modelName": modelName})
			modelName = ""
		}
	}
	return &MemoryStore{
		db:        db,
		agentID:   agentID,
		embedding: embedding,
		modelName: modelName,
	}
}

// ReadLongTerm reads all long-term memories, joined with "---" separator.
func (ms *MemoryStore) ReadLongTerm() string {
	// Order by importance with time-decay: recently accessed memories rank higher
	rows, err := ms.db.Query(
		"SELECT content FROM PICO_MEMORIES WHERE agent_id = :1 ORDER BY (importance * (1.0 / (1.0 + (SYSDATE - CAST(NVL(accessed_at, created_at) AS DATE)) * 0.1))) DESC, CAST(created_at AS DATE) DESC FETCH FIRST 50 ROWS ONLY",
		ms.agentID,
	)
	if err != nil {
		logger.WarnCF("oracle", "Failed to read long-term memories", map[string]interface{}{"error": err.Error()})
		return ""
	}
	defer rows.Close()

	var parts []string
	for rows.Next() {
		var content sql.NullString
		if err := rows.Scan(&content); err == nil && content.Valid {
			parts = append(parts, content.String)
		}
	}

	return strings.Join(parts, "\n\n---\n\n")
}

// WriteLongTerm stores a new long-term memory with embedding.
func (ms *MemoryStore) WriteLongTerm(content string) error {
	_, err := ms.Remember(content, 0.7, "long_term")
	return err
}

// ReadToday reads today's daily note.
func (ms *MemoryStore) ReadToday() string {
	var content sql.NullString
	err := ms.db.QueryRow(
		"SELECT content FROM PICO_DAILY_NOTES WHERE agent_id = :1 AND note_date = TRUNC(SYSDATE) ORDER BY updated_at DESC FETCH FIRST 1 ROW ONLY",
		ms.agentID,
	).Scan(&content)
	if err != nil || !content.Valid {
		return ""
	}
	return content.String
}

// AppendToday appends content to today's daily note.
func (ms *MemoryStore) AppendToday(content string) error {
	// Try to get existing today note
	existing := ms.ReadToday()

	if existing == "" {
		// Insert new daily note
		header := fmt.Sprintf("# %s\n\n", time.Now().Format("2006-01-02"))
		fullContent := header + content

		noteID := uuid.New().String()[:8]

		if ms.modelName != "" && ms.embedding != nil && ms.embedding.Mode() == "onnx" {
			query := fmt.Sprintf(`
				INSERT INTO PICO_DAILY_NOTES (note_id, agent_id, note_date, content, embedding)
				VALUES (:1, :2, TRUNC(SYSDATE), :3, VECTOR_EMBEDDING(%s USING :4 AS DATA))`,
				ms.modelName,
			)
			_, err := ms.db.Exec(query, noteID, ms.agentID, fullContent, fullContent)
			return err
		}

		_, err := ms.db.Exec(`
			INSERT INTO PICO_DAILY_NOTES (note_id, agent_id, note_date, content)
			VALUES (:1, :2, TRUNC(SYSDATE), :3)`,
			noteID, ms.agentID, fullContent,
		)
		return err
	}

	// Append to existing
	newContent := existing + "\n" + content

	if ms.modelName != "" && ms.embedding != nil && ms.embedding.Mode() == "onnx" {
		query := fmt.Sprintf(`
			UPDATE PICO_DAILY_NOTES
			SET content = :1, embedding = VECTOR_EMBEDDING(%s USING :2 AS DATA), updated_at = CURRENT_TIMESTAMP
			WHERE agent_id = :3 AND note_date = TRUNC(SYSDATE)`,
			ms.modelName,
		)
		_, err := ms.db.Exec(query, newContent, newContent, ms.agentID)
		return err
	}

	_, err := ms.db.Exec(`
		UPDATE PICO_DAILY_NOTES
		SET content = :1, updated_at = CURRENT_TIMESTAMP
		WHERE agent_id = :2 AND note_date = TRUNC(SYSDATE)`,
		newContent, ms.agentID,
	)
	return err
}

// GetRecentDailyNotes returns daily notes from the last N days.
func (ms *MemoryStore) GetRecentDailyNotes(days int) string {
	rows, err := ms.db.Query(
		"SELECT content FROM PICO_DAILY_NOTES WHERE agent_id = :1 AND note_date >= TRUNC(SYSDATE) - :2 ORDER BY note_date DESC",
		ms.agentID, days,
	)
	if err != nil {
		logger.WarnCF("oracle", "Failed to read recent daily notes", map[string]interface{}{"error": err.Error()})
		return ""
	}
	defer rows.Close()

	var notes []string
	for rows.Next() {
		var content sql.NullString
		if err := rows.Scan(&content); err == nil && content.Valid {
			notes = append(notes, content.String)
		}
	}

	if len(notes) == 0 {
		return ""
	}

	var sb strings.Builder
	for i, note := range notes {
		if i > 0 {
			sb.WriteString("\n\n---\n\n")
		}
		sb.WriteString(note)
	}
	return sb.String()
}

// GetMemoryContext returns formatted memory context for the agent prompt.
func (ms *MemoryStore) GetMemoryContext() string {
	var parts []string

	longTerm := ms.ReadLongTerm()
	if longTerm != "" {
		parts = append(parts, "## Long-term Memory\n\n"+longTerm)
	}

	recentNotes := ms.GetRecentDailyNotes(3)
	if recentNotes != "" {
		parts = append(parts, "## Recent Daily Notes\n\n"+recentNotes)
	}

	if len(parts) == 0 {
		return ""
	}

	var sb strings.Builder
	for i, part := range parts {
		if i > 0 {
			sb.WriteString("\n\n---\n\n")
		}
		sb.WriteString(part)
	}
	return fmt.Sprintf("# Memory\n\n%s", sb.String())
}

// Remember stores a new memory with embedding for vector search.
// Uses Oracle's in-database VECTOR_EMBEDDING() to compute the embedding inline.
// Checks for near-duplicate memories before inserting to prevent clutter.
func (ms *MemoryStore) Remember(text string, importance float64, category string) (string, error) {
	// Check for near-duplicate memories before inserting
	if existingID, updated := ms.deduplicateMemory(text, importance); updated {
		return existingID, nil
	}

	memoryID := uuid.New().String()[:8]

	if ms.modelName != "" && ms.embedding != nil && ms.embedding.Mode() == "onnx" {
		// Use VECTOR_EMBEDDING() inline - Oracle computes the embedding in-database
		// Pass text twice: once for content column, once for VECTOR_EMBEDDING
		query := fmt.Sprintf(`
			INSERT INTO PICO_MEMORIES (memory_id, agent_id, content, embedding, importance, category)
			VALUES (:1, :2, :3, VECTOR_EMBEDDING(%s USING :4 AS DATA), :5, :6)`,
			ms.modelName,
		)
		_, err := ms.db.Exec(query, memoryID, ms.agentID, text, text, importance, category)
		if err != nil {
			return "", fmt.Errorf("failed to remember: %w", err)
		}
	} else if ms.embedding != nil && ms.embedding.Mode() == "api" {
		// API mode: compute embedding via external API, convert to string for TO_VECTOR()
		emb, err := ms.embedding.EmbedText(text)
		if err != nil {
			logger.WarnCF("oracle", "Embedding failed, storing without vector", map[string]interface{}{"error": err.Error()})
			_, err = ms.db.Exec(`
				INSERT INTO PICO_MEMORIES (memory_id, agent_id, content, importance, category)
				VALUES (:1, :2, :3, :4, :5)`,
				memoryID, ms.agentID, text, importance, category,
			)
			if err != nil {
				return "", fmt.Errorf("failed to remember: %w", err)
			}
		} else {
			vecStr := float32SliceToString(emb)
			_, err = ms.db.Exec(`
				INSERT INTO PICO_MEMORIES (memory_id, agent_id, content, embedding, importance, category)
				VALUES (:1, :2, :3, TO_VECTOR(:4), :5, :6)`,
				memoryID, ms.agentID, text, vecStr, importance, category,
			)
			if err != nil {
				return "", fmt.Errorf("failed to remember: %w", err)
			}
		}
	} else {
		// No embedding available
		_, err := ms.db.Exec(`
			INSERT INTO PICO_MEMORIES (memory_id, agent_id, content, importance, category)
			VALUES (:1, :2, :3, :4, :5)`,
			memoryID, ms.agentID, text, importance, category,
		)
		if err != nil {
			return "", fmt.Errorf("failed to remember: %w", err)
		}
	}

	logger.InfoCF("oracle", "Memory stored", map[string]interface{}{
		"memory_id":  memoryID,
		"importance": importance,
		"category":   category,
	})
	return memoryID, nil
}

// Recall performs semantic similarity search on memories.
func (ms *MemoryStore) Recall(query string, maxResults int) ([]MemoryRecallResult, error) {
	if ms.embedding == nil {
		return nil, fmt.Errorf("embedding service not available")
	}

	var rows *sql.Rows
	var err error

	if ms.modelName != "" && ms.embedding.Mode() == "onnx" {
		// Use VECTOR_EMBEDDING() inline for query embedding
		sqlQuery := fmt.Sprintf(`
			SELECT memory_id, content, importance, category,
			       VECTOR_DISTANCE(embedding, VECTOR_EMBEDDING(%s USING :1 AS DATA), COSINE) AS distance
			FROM PICO_MEMORIES
			WHERE agent_id = :2 AND embedding IS NOT NULL
			ORDER BY distance ASC
			FETCH FIRST :3 ROWS ONLY`, ms.modelName)
		rows, err = ms.db.Query(sqlQuery, query, ms.agentID, maxResults)
	} else {
		// API mode: compute embedding externally, use TO_VECTOR()
		queryVec, embErr := ms.embedding.EmbedText(query)
		if embErr != nil {
			return nil, fmt.Errorf("failed to embed query: %w", embErr)
		}
		vecStr := float32SliceToString(queryVec)
		rows, err = ms.db.Query(`
			SELECT memory_id, content, importance, category,
			       VECTOR_DISTANCE(embedding, TO_VECTOR(:1), COSINE) AS distance
			FROM PICO_MEMORIES
			WHERE agent_id = :2 AND embedding IS NOT NULL
			ORDER BY distance ASC
			FETCH FIRST :3 ROWS ONLY`,
			vecStr, ms.agentID, maxResults)
	}
	if err != nil {
		return nil, fmt.Errorf("recall query failed: %w", err)
	}
	defer rows.Close()

	var results []MemoryRecallResult
	var memoryIDs []string

	for rows.Next() {
		var r MemoryRecallResult
		var content sql.NullString
		var category sql.NullString
		var distance float64

		if err := rows.Scan(&r.MemoryID, &content, &r.Importance, &category, &distance); err != nil {
			continue
		}

		if content.Valid {
			r.Text = content.String
		}
		if category.Valid {
			r.Category = category.String
		}
		r.Score = 1.0 - distance

		if r.Score >= 0.3 { // Minimum similarity threshold
			results = append(results, r)
			memoryIDs = append(memoryIDs, r.MemoryID)
		}
	}

	// Update access timestamps for recalled memories
	if len(memoryIDs) > 0 {
		ms.updateAccessTimestamps(memoryIDs)
	}

	return results, nil
}

// Forget deletes a memory by ID.
func (ms *MemoryStore) Forget(memoryID string) error {
	result, err := ms.db.Exec(
		"DELETE FROM PICO_MEMORIES WHERE memory_id = :1 AND agent_id = :2",
		memoryID, ms.agentID,
	)
	if err != nil {
		return fmt.Errorf("forget failed: %w", err)
	}

	affected, _ := result.RowsAffected()
	if affected == 0 {
		return fmt.Errorf("memory %s not found", memoryID)
	}
	return nil
}

// float32SliceToString converts a float32 slice to Oracle VECTOR string format.
// Example output: "[0.123,0.456,-0.789]"
func float32SliceToString(v []float32) string {
	if len(v) == 0 {
		return "[]"
	}
	var sb strings.Builder
	sb.Grow(len(v)*8 + 2) // pre-allocate roughly
	sb.WriteByte('[')
	for i, f := range v {
		if i > 0 {
			sb.WriteByte(',')
		}
		fmt.Fprintf(&sb, "%g", f)
	}
	sb.WriteByte(']')
	return sb.String()
}

// updateAccessTimestamps updates access_count and accessed_at for recalled memories
// using a single batch UPDATE to avoid N+1 query overhead.
func (ms *MemoryStore) updateAccessTimestamps(memoryIDs []string) {
	if len(memoryIDs) == 0 {
		return
	}
	placeholders := make([]string, len(memoryIDs))
	args := make([]interface{}, len(memoryIDs))
	for i, id := range memoryIDs {
		placeholders[i] = fmt.Sprintf(":%d", i+1)
		args[i] = id
	}
	query := fmt.Sprintf(
		"UPDATE PICO_MEMORIES SET accessed_at = CURRENT_TIMESTAMP, access_count = access_count + 1 WHERE memory_id IN (%s)",
		strings.Join(placeholders, ", "),
	)
	if _, err := ms.db.Exec(query, args...); err != nil {
		logger.WarnCF("oracle", "Failed to update access timestamps", map[string]interface{}{"error": err.Error()})
	}
}

// deduplicateMemory checks for near-duplicate memories before inserting.
// Returns (existingID, true) if a duplicate was found and updated, or ("", false) if no duplicate.
func (ms *MemoryStore) deduplicateMemory(text string, importance float64) (string, bool) {
	// Try exact text match first (cheap)
	var existingID string
	var existingImportance float64
	err := ms.db.QueryRow(
		"SELECT memory_id, importance FROM PICO_MEMORIES WHERE agent_id = :1 AND content = :2 FETCH FIRST 1 ROW ONLY",
		ms.agentID, text,
	).Scan(&existingID, &existingImportance)
	if err == nil {
		// Exact match found - update importance if new one is higher
		if importance > existingImportance {
			if _, execErr := ms.db.Exec("UPDATE PICO_MEMORIES SET importance = :1, accessed_at = CURRENT_TIMESTAMP WHERE memory_id = :2",
				importance, existingID); execErr != nil {
				logger.WarnCF("oracle", "Failed to update importance for duplicate memory", map[string]interface{}{
					"memory_id": existingID, "error": execErr.Error()})
			}
		}
		logger.InfoCF("oracle", "Duplicate memory detected, reusing existing", map[string]interface{}{
			"memory_id": existingID,
		})
		return existingID, true
	}

	// Try semantic deduplication via vector similarity if ONNX is available
	if ms.modelName != "" && ms.embedding != nil && ms.embedding.Mode() == "onnx" {
		sqlQuery := fmt.Sprintf(`
			SELECT memory_id, importance,
			       VECTOR_DISTANCE(embedding, VECTOR_EMBEDDING(%s USING :1 AS DATA), COSINE) AS distance
			FROM PICO_MEMORIES
			WHERE agent_id = :2 AND embedding IS NOT NULL
			ORDER BY distance ASC
			FETCH FIRST 1 ROW ONLY`, ms.modelName)
		var distance float64
		err := ms.db.QueryRow(sqlQuery, text, ms.agentID).Scan(&existingID, &existingImportance, &distance)
		if err == nil && distance < 0.05 { // 95%+ similarity
			if importance > existingImportance {
				if _, execErr := ms.db.Exec("UPDATE PICO_MEMORIES SET importance = :1, accessed_at = CURRENT_TIMESTAMP WHERE memory_id = :2",
					importance, existingID); execErr != nil {
					logger.WarnCF("oracle", "Failed to update importance for near-duplicate memory", map[string]interface{}{
						"memory_id": existingID, "error": execErr.Error()})
				}
			}
			logger.InfoCF("oracle", "Near-duplicate memory detected via embedding similarity", map[string]interface{}{
				"memory_id": existingID,
				"distance":  distance,
			})
			return existingID, true
		}
	}

	return "", false
}
