package tools

import (
	"context"
	"fmt"
)

// Rememberer is the interface the remember tool needs to store memories.
type Rememberer interface {
	Remember(text string, importance float64, category string) (string, error)
}

// RememberTool provides the "remember" tool for storing memories with vector embeddings.
type RememberTool struct {
	store Rememberer
}

// NewRememberTool creates a new remember tool.
func NewRememberTool(store Rememberer) *RememberTool {
	return &RememberTool{store: store}
}

func (t *RememberTool) Name() string { return "remember" }

func (t *RememberTool) Description() string {
	return "Store a piece of information in long-term memory with vector embedding for later semantic recall. Use this to remember facts, preferences, or important context."
}

func (t *RememberTool) Parameters() map[string]interface{} {
	return map[string]interface{}{
		"type": "object",
		"properties": map[string]interface{}{
			"text": map[string]interface{}{
				"type":        "string",
				"description": "The text content to remember",
			},
			"importance": map[string]interface{}{
				"type":        "number",
				"description": "Importance score from 0.0 to 1.0 (default: 0.7)",
			},
			"category": map[string]interface{}{
				"type":        "string",
				"description": "Optional category for organizing memories (e.g., 'preference', 'fact', 'context')",
			},
		},
		"required": []string{"text"},
	}
}

func (t *RememberTool) Execute(ctx context.Context, args map[string]interface{}) *ToolResult {
	text, _ := args["text"].(string)
	if text == "" {
		return ErrorResult("text parameter is required")
	}

	importance := 0.7
	if imp, ok := args["importance"].(float64); ok {
		if imp >= 0 && imp <= 1 {
			importance = imp
		}
	}

	category := ""
	if cat, ok := args["category"].(string); ok {
		category = cat
	}

	memoryID, err := t.store.Remember(text, importance, category)
	if err != nil {
		return ErrorResult(fmt.Sprintf("Failed to remember: %v", err))
	}

	return NewToolResult(fmt.Sprintf("Remembered (ID: %s, importance: %.1f, category: %s): %s",
		memoryID, importance, category, truncate(text, 100)))
}

func truncate(s string, maxLen int) string {
	if len(s) <= maxLen {
		return s
	}
	return s[:maxLen] + "..."
}
