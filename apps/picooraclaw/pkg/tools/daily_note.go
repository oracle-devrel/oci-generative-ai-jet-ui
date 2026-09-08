package tools

import (
	"context"
	"fmt"
)

// DailyNoteWriter is the interface the write_daily_note tool needs.
type DailyNoteWriter interface {
	AppendToday(content string) error
}

// WriteDailyNoteTool provides the "write_daily_note" tool for appending to today's journal.
type WriteDailyNoteTool struct {
	store DailyNoteWriter
}

// NewWriteDailyNoteTool creates a new write_daily_note tool backed by the given store.
func NewWriteDailyNoteTool(store DailyNoteWriter) *WriteDailyNoteTool {
	return &WriteDailyNoteTool{store: store}
}

func (t *WriteDailyNoteTool) Name() string { return "write_daily_note" }

func (t *WriteDailyNoteTool) Description() string {
	return "Append a note to today's daily journal. Use this to record events, tasks completed, observations, or anything worth noting for today. Notes are stored persistently and included in future context."
}

func (t *WriteDailyNoteTool) Parameters() map[string]interface{} {
	return map[string]interface{}{
		"type": "object",
		"properties": map[string]interface{}{
			"content": map[string]interface{}{
				"type":        "string",
				"description": "The note content to append to today's daily journal",
			},
		},
		"required": []string{"content"},
	}
}

func (t *WriteDailyNoteTool) Execute(ctx context.Context, args map[string]interface{}) *ToolResult {
	content, _ := args["content"].(string)
	if content == "" {
		return ErrorResult("content parameter is required")
	}

	if err := t.store.AppendToday(content); err != nil {
		return ErrorResult(fmt.Sprintf("Failed to write daily note: %v", err))
	}

	return NewToolResult(fmt.Sprintf("Daily note written: %s", truncate(content, 100)))
}
