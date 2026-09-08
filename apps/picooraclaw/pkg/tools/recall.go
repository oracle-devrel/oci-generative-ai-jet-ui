package tools

import (
	"context"
	"fmt"
	"strings"
)

// RecallResult represents a recalled memory.
type RecallResult struct {
	MemoryID   string
	Text       string
	Importance float64
	Category   string
	Score      float64
}

// Recaller is the interface the recall tool needs for semantic memory search.
type Recaller interface {
	Recall(query string, maxResults int) ([]RecallResult, error)
}

// RecallTool provides the "recall" tool for semantic memory search.
type RecallTool struct {
	store Recaller
}

// NewRecallTool creates a new recall tool.
func NewRecallTool(store Recaller) *RecallTool {
	return &RecallTool{store: store}
}

func (t *RecallTool) Name() string { return "recall" }

func (t *RecallTool) Description() string {
	return "Search long-term memory using semantic similarity. Use this to find previously remembered information by describing what you're looking for."
}

func (t *RecallTool) Parameters() map[string]interface{} {
	return map[string]interface{}{
		"type": "object",
		"properties": map[string]interface{}{
			"query": map[string]interface{}{
				"type":        "string",
				"description": "Search query describing what to recall",
			},
			"max_results": map[string]interface{}{
				"type":        "integer",
				"description": "Maximum number of results to return (default: 5)",
			},
		},
		"required": []string{"query"},
	}
}

func (t *RecallTool) Execute(ctx context.Context, args map[string]interface{}) *ToolResult {
	query, _ := args["query"].(string)
	if query == "" {
		return ErrorResult("query parameter is required")
	}

	maxResults := 5
	if mr, ok := args["max_results"].(float64); ok && mr > 0 {
		maxResults = int(mr)
	}

	results, err := t.store.Recall(query, maxResults)
	if err != nil {
		return ErrorResult(fmt.Sprintf("Recall failed: %v", err))
	}

	if len(results) == 0 {
		return NewToolResult("No matching memories found for: " + query)
	}

	var sb strings.Builder
	sb.WriteString(fmt.Sprintf("Found %d matching memories:\n\n", len(results)))
	for i, r := range results {
		sb.WriteString(fmt.Sprintf("%d. [%.0f%% match] (ID: %s", i+1, r.Score*100, r.MemoryID))
		if r.Category != "" {
			sb.WriteString(fmt.Sprintf(", category: %s", r.Category))
		}
		sb.WriteString(fmt.Sprintf(", importance: %.1f)\n", r.Importance))
		sb.WriteString(fmt.Sprintf("   %s\n\n", r.Text))
	}

	return NewToolResult(sb.String())
}
