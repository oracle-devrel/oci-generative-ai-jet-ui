package oracle

import (
	"database/sql"
	"fmt"
	"os"
	"path/filepath"

	"github.com/jasperan/picooraclaw/pkg/logger"
)

// PromptStore manages system prompts in Oracle PICO_PROMPTS.
type PromptStore struct {
	db      *sql.DB
	agentID string
}

// NewPromptStore creates a new Oracle-backed prompt store.
func NewPromptStore(db *sql.DB, agentID string) *PromptStore {
	return &PromptStore{
		db:      db,
		agentID: agentID,
	}
}

// LoadPrompt retrieves a named prompt from Oracle.
func (ps *PromptStore) LoadPrompt(name string) (string, error) {
	var content sql.NullString
	err := ps.db.QueryRow(
		"SELECT content FROM PICO_PROMPTS WHERE prompt_name = :1 AND agent_id = :2",
		name, ps.agentID,
	).Scan(&content)
	if err != nil {
		if err == sql.ErrNoRows {
			return "", nil
		}
		return "", fmt.Errorf("failed to load prompt %s: %w", name, err)
	}
	if !content.Valid {
		return "", nil
	}
	return content.String, nil
}

// SavePrompt upserts a prompt using MERGE INTO.
func (ps *PromptStore) SavePrompt(name, content string) error {
	_, err := ps.db.Exec(`
		MERGE INTO PICO_PROMPTS p
		USING (SELECT :1 AS prompt_name, :2 AS agent_id FROM DUAL) src
		ON (p.prompt_name = src.prompt_name AND p.agent_id = src.agent_id)
		WHEN MATCHED THEN
			UPDATE SET content = :3, updated_at = CURRENT_TIMESTAMP
		WHEN NOT MATCHED THEN
			INSERT (prompt_name, agent_id, content) VALUES (:4, :5, :6)
	`, name, ps.agentID, content, name, ps.agentID, content)
	if err != nil {
		return fmt.Errorf("failed to save prompt %s: %w", name, err)
	}
	return nil
}

// LoadBootstrapFiles returns a map of all prompts for context builder.
func (ps *PromptStore) LoadBootstrapFiles() map[string]string {
	result := make(map[string]string)

	rows, err := ps.db.Query(
		"SELECT prompt_name, content FROM PICO_PROMPTS WHERE agent_id = :1",
		ps.agentID,
	)
	if err != nil {
		logger.WarnCF("oracle", "Failed to load bootstrap prompts from Oracle", map[string]interface{}{
			"agent_id": ps.agentID,
			"error":    err.Error(),
		})
		return result
	}
	defer rows.Close()

	for rows.Next() {
		var name string
		var content sql.NullString
		if err := rows.Scan(&name, &content); err == nil && content.Valid {
			result[name] = content.String
		}
	}
	return result
}

// SeedFromWorkspace reads workspace .md files and stores them as prompts.
func (ps *PromptStore) SeedFromWorkspace(workspacePath string) error {
	files := []string{"IDENTITY.md", "SOUL.md", "USER.md", "AGENT.md", "AGENTS.md"}

	seeded := 0
	for _, filename := range files {
		filePath := filepath.Join(workspacePath, filename)
		data, err := os.ReadFile(filePath)
		if err != nil {
			continue // File doesn't exist, skip
		}

		promptName := filename[:len(filename)-3] // Remove .md extension
		if err := ps.SavePrompt(promptName, string(data)); err != nil {
			logger.WarnCF("oracle", "Failed to seed prompt", map[string]interface{}{
				"file":  filename,
				"error": err.Error(),
			})
			continue
		}
		seeded++
	}

	if seeded > 0 {
		logger.InfoCF("oracle", "Seeded prompts from workspace", map[string]interface{}{"count": seeded})
	}
	return nil
}
