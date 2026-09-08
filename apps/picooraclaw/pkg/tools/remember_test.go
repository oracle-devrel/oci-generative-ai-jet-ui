package tools

import (
	"context"
	"testing"
)

// mockRememberer implements the Rememberer interface for testing.
type mockRememberer struct {
	lastText       string
	lastImportance float64
	lastCategory   string
	shouldFail     bool
}

func (m *mockRememberer) Remember(text string, importance float64, category string) (string, error) {
	m.lastText = text
	m.lastImportance = importance
	m.lastCategory = category
	if m.shouldFail {
		return "", context.DeadlineExceeded
	}
	return "mem-abc1", nil
}

func TestRememberTool_Name(t *testing.T) {
	tool := NewRememberTool(&mockRememberer{})
	if tool.Name() != "remember" {
		t.Errorf("Name() = %q, want %q", tool.Name(), "remember")
	}
}

func TestRememberTool_Parameters(t *testing.T) {
	tool := NewRememberTool(&mockRememberer{})
	params := tool.Parameters()
	if params == nil {
		t.Fatal("Parameters() returned nil")
	}
	props, ok := params["properties"].(map[string]interface{})
	if !ok {
		t.Fatal("parameters missing properties")
	}
	if _, ok := props["text"]; !ok {
		t.Error("parameters missing 'text' property")
	}
	if _, ok := props["importance"]; !ok {
		t.Error("parameters missing 'importance' property")
	}
	if _, ok := props["category"]; !ok {
		t.Error("parameters missing 'category' property")
	}
}

func TestRememberTool_ExecuteBasic(t *testing.T) {
	store := &mockRememberer{}
	tool := NewRememberTool(store)

	result := tool.Execute(context.Background(), map[string]interface{}{
		"text": "My favorite color is blue",
	})

	if result.IsError {
		t.Fatalf("Execute failed: %s", result.ForLLM)
	}
	if store.lastText != "My favorite color is blue" {
		t.Errorf("stored text = %q", store.lastText)
	}
	if store.lastImportance != 0.7 {
		t.Errorf("default importance = %f, want 0.7", store.lastImportance)
	}
}

func TestRememberTool_ExecuteWithAllParams(t *testing.T) {
	store := &mockRememberer{}
	tool := NewRememberTool(store)

	result := tool.Execute(context.Background(), map[string]interface{}{
		"text":       "User prefers dark mode",
		"importance": 0.9,
		"category":   "preference",
	})

	if result.IsError {
		t.Fatalf("Execute failed: %s", result.ForLLM)
	}
	if store.lastImportance != 0.9 {
		t.Errorf("importance = %f, want 0.9", store.lastImportance)
	}
	if store.lastCategory != "preference" {
		t.Errorf("category = %q, want %q", store.lastCategory, "preference")
	}
}

func TestRememberTool_ExecuteMissingText(t *testing.T) {
	tool := NewRememberTool(&mockRememberer{})

	result := tool.Execute(context.Background(), map[string]interface{}{})
	if !result.IsError {
		t.Error("should fail when text is missing")
	}
}

func TestRememberTool_ExecuteStoreFailure(t *testing.T) {
	store := &mockRememberer{shouldFail: true}
	tool := NewRememberTool(store)

	result := tool.Execute(context.Background(), map[string]interface{}{
		"text": "test",
	})
	if !result.IsError {
		t.Error("should report error when store fails")
	}
}

func TestRememberTool_ImportanceClamping(t *testing.T) {
	store := &mockRememberer{}
	tool := NewRememberTool(store)

	// Out of range importance should use default
	tool.Execute(context.Background(), map[string]interface{}{
		"text":       "test",
		"importance": 1.5, // out of range
	})
	if store.lastImportance != 0.7 {
		t.Errorf("out-of-range importance should fallback to 0.7, got %f", store.lastImportance)
	}

	tool.Execute(context.Background(), map[string]interface{}{
		"text":       "test",
		"importance": -0.5, // out of range
	})
	if store.lastImportance != 0.7 {
		t.Errorf("negative importance should fallback to 0.7, got %f", store.lastImportance)
	}
}
