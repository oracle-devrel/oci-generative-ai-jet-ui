package tools

import (
	"context"
	"fmt"
	"strings"
	"testing"
)

// mockRecaller implements the Recaller interface for testing.
type mockRecaller struct {
	results    []RecallResult
	shouldFail bool
	lastQuery  string
	lastMax    int
}

func (m *mockRecaller) Recall(query string, maxResults int) ([]RecallResult, error) {
	m.lastQuery = query
	m.lastMax = maxResults
	if m.shouldFail {
		return nil, fmt.Errorf("recall failed")
	}
	return m.results, nil
}

func TestRecallTool_Name(t *testing.T) {
	tool := NewRecallTool(&mockRecaller{})
	if tool.Name() != "recall" {
		t.Errorf("Name() = %q, want %q", tool.Name(), "recall")
	}
}

func TestRecallTool_Parameters(t *testing.T) {
	tool := NewRecallTool(&mockRecaller{})
	params := tool.Parameters()
	props, ok := params["properties"].(map[string]interface{})
	if !ok {
		t.Fatal("parameters missing properties")
	}
	if _, ok := props["query"]; !ok {
		t.Error("parameters missing 'query' property")
	}
	if _, ok := props["max_results"]; !ok {
		t.Error("parameters missing 'max_results' property")
	}
}

func TestRecallTool_ExecuteWithResults(t *testing.T) {
	store := &mockRecaller{
		results: []RecallResult{
			{MemoryID: "mem-1", Text: "Favorite color is blue", Score: 0.95, Importance: 0.8, Category: "preference"},
			{MemoryID: "mem-2", Text: "Lives in Madrid", Score: 0.72, Importance: 0.6, Category: "fact"},
		},
	}
	tool := NewRecallTool(store)

	result := tool.Execute(context.Background(), map[string]interface{}{
		"query": "what color do they like",
	})

	if result.IsError {
		t.Fatalf("Execute failed: %s", result.ForLLM)
	}
	if store.lastQuery != "what color do they like" {
		t.Errorf("query = %q", store.lastQuery)
	}
	if store.lastMax != 5 {
		t.Errorf("default max_results = %d, want 5", store.lastMax)
	}
	if !strings.Contains(result.ForLLM, "2 matching memories") {
		t.Errorf("result should mention 2 matches: %s", result.ForLLM)
	}
	if !strings.Contains(result.ForLLM, "95%") {
		t.Errorf("result should contain score percentage: %s", result.ForLLM)
	}
	if !strings.Contains(result.ForLLM, "preference") {
		t.Errorf("result should contain category: %s", result.ForLLM)
	}
}

func TestRecallTool_ExecuteNoResults(t *testing.T) {
	store := &mockRecaller{results: []RecallResult{}}
	tool := NewRecallTool(store)

	result := tool.Execute(context.Background(), map[string]interface{}{
		"query": "something obscure",
	})

	if result.IsError {
		t.Fatalf("Execute failed: %s", result.ForLLM)
	}
	if !strings.Contains(result.ForLLM, "No matching memories") {
		t.Errorf("should indicate no matches: %s", result.ForLLM)
	}
}

func TestRecallTool_ExecuteMissingQuery(t *testing.T) {
	tool := NewRecallTool(&mockRecaller{})

	result := tool.Execute(context.Background(), map[string]interface{}{})
	if !result.IsError {
		t.Error("should fail when query is missing")
	}
}

func TestRecallTool_ExecuteCustomMaxResults(t *testing.T) {
	store := &mockRecaller{results: []RecallResult{}}
	tool := NewRecallTool(store)

	tool.Execute(context.Background(), map[string]interface{}{
		"query":       "test",
		"max_results": float64(10),
	})

	if store.lastMax != 10 {
		t.Errorf("max_results = %d, want 10", store.lastMax)
	}
}

func TestRecallTool_ExecuteStoreFailure(t *testing.T) {
	store := &mockRecaller{shouldFail: true}
	tool := NewRecallTool(store)

	result := tool.Execute(context.Background(), map[string]interface{}{
		"query": "test",
	})
	if !result.IsError {
		t.Error("should report error when store fails")
	}
}
