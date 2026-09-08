package tools

import (
	"context"
	"fmt"
)

type SpawnTool struct {
	manager *SubagentManager
}

func NewSpawnTool(manager *SubagentManager) *SpawnTool {
	return &SpawnTool{
		manager: manager,
	}
}

func (t *SpawnTool) Name() string {
	return "spawn"
}

func (t *SpawnTool) Description() string {
	return "Spawn a subagent to handle a task in the background. Use this for complex or time-consuming tasks that can run independently. The subagent will complete the task and report back when done."
}

func (t *SpawnTool) Parameters() map[string]interface{} {
	return map[string]interface{}{
		"type": "object",
		"properties": map[string]interface{}{
			"task": map[string]interface{}{
				"type":        "string",
				"description": "The task for subagent to complete",
			},
			"label": map[string]interface{}{
				"type":        "string",
				"description": "Optional short label for the task (for display)",
			},
		},
		"required": []string{"task"},
	}
}

func (t *SpawnTool) Execute(ctx context.Context, args map[string]interface{}) *ToolResult {
	task, ok := args["task"].(string)
	if !ok {
		return ErrorResult("task is required")
	}

	label, _ := args["label"].(string)

	if t.manager == nil {
		return ErrorResult("Subagent manager not configured")
	}

	// Read channel/chatID from context
	channel := ToolChannel(ctx)
	chatID := ToolChatID(ctx)
	if channel == "" {
		channel = "cli"
	}
	if chatID == "" {
		chatID = "direct"
	}

	// Return AsyncResult since the task runs in background; callback handled via ExecuteAsync
	result, err := t.manager.Spawn(ctx, task, label, channel, chatID, nil)
	if err != nil {
		return ErrorResult(fmt.Sprintf("failed to spawn subagent: %v", err))
	}

	return AsyncResult(result)
}

// ExecuteAsync implements AsyncExecutor — receives callback as a parameter
// so there is no mutable state on the singleton tool instance.
func (t *SpawnTool) ExecuteAsync(ctx context.Context, args map[string]interface{}, cb AsyncCallback) *ToolResult {
	task, ok := args["task"].(string)
	if !ok {
		return ErrorResult("task is required")
	}

	label, _ := args["label"].(string)

	if t.manager == nil {
		return ErrorResult("Subagent manager not configured")
	}

	// Read channel/chatID from context
	channel := ToolChannel(ctx)
	chatID := ToolChatID(ctx)
	if channel == "" {
		channel = "cli"
	}
	if chatID == "" {
		chatID = "direct"
	}

	result, err := t.manager.Spawn(ctx, task, label, channel, chatID, cb)
	if err != nil {
		return ErrorResult(fmt.Sprintf("failed to spawn subagent: %v", err))
	}

	return AsyncResult(result)
}
