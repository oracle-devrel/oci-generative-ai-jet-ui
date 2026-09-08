package viz

import (
	"strings"
	"testing"

	"agent-reasoning-tui/internal/client"
)

// TestRegistryCoversAll ensures all 13 agent keys have constructors.
func TestRegistryCoversAll(t *testing.T) {
	expected := []string{
		"cot", "tot", "mcts", "react", "consistency",
		"reflection", "refinement", "complex_refinement",
		"debate", "socratic", "analogical", "decomposed", "least_to_most",
	}
	for _, id := range expected {
		if _, ok := Registry[id]; !ok {
			t.Errorf("Registry missing key: %s", id)
		}
	}
	if len(Registry) != len(expected) {
		t.Errorf("Registry has %d keys, expected %d", len(Registry), len(expected))
	}
}

// TestRegistryReturnsNilForStandard ensures text-only agents return nil.
func TestRegistryReturnsNilForStandard(t *testing.T) {
	v := GetVisualizer("standard", 80, 24)
	if v != nil {
		t.Error("expected nil for standard agent")
	}
	v2 := GetVisualizer("nonexistent", 80, 24)
	if v2 != nil {
		t.Error("expected nil for nonexistent agent")
	}
}

// TestStepsVizBasic verifies chain_step events produce labeled output.
func TestStepsVizBasic(t *testing.T) {
	v := NewStepsViz(80, 24)

	v.Update(client.StructuredEvent{
		EventType: "chain_step",
		Data:      map[string]interface{}{"step": float64(1), "content": "First step reasoning"},
	})
	v.Update(client.StructuredEvent{
		EventType: "chain_step",
		Data:      map[string]interface{}{"step": float64(2), "content": "Second step reasoning"},
	})
	v.Update(client.StructuredEvent{
		EventType: "final",
		Data:      map[string]interface{}{"content": "The final answer is 42"},
	})

	out := v.View()
	if !strings.Contains(out, "Step 1") {
		t.Error("expected 'Step 1' in output")
	}
	if !strings.Contains(out, "Step 2") {
		t.Error("expected 'Step 2' in output")
	}
	if !strings.Contains(out, "Answer") {
		t.Error("expected 'Answer' in output")
	}
	if !strings.Contains(out, "First step reasoning") {
		t.Error("expected step content in output")
	}
}

// TestTreeVizNodeAdding verifies node events render in tree output.
func TestTreeVizNodeAdding(t *testing.T) {
	v := NewTreeViz(80, 24)

	v.Update(client.StructuredEvent{
		EventType: "node",
		Data:      map[string]interface{}{"id": "root", "content": "Root thought", "score": float64(0.5), "depth": float64(0)},
	})
	v.Update(client.StructuredEvent{
		EventType: "node",
		Data:      map[string]interface{}{"id": "child1", "content": "Child thought A", "score": float64(0.7), "depth": float64(1), "parent_id": "root"},
	})
	v.Update(client.StructuredEvent{
		EventType: "node",
		Data:      map[string]interface{}{"id": "child2", "content": "Child thought B", "score": float64(0.3), "depth": float64(1), "parent_id": "root"},
	})

	out := v.View()
	if out == "" || out == "Waiting for tree nodes..." {
		t.Error("expected non-empty tree output after adding nodes")
	}
	if !strings.Contains(out, "Root thought") {
		t.Error("expected root content in tree output")
	}
}

// TestTreeVizHighlight verifies final event triggers highlight path.
func TestTreeVizHighlight(t *testing.T) {
	v := NewTreeViz(80, 24)

	v.Update(client.StructuredEvent{
		EventType: "node",
		Data:      map[string]interface{}{"id": "n1", "content": "Node one", "score": float64(0.9), "depth": float64(0)},
	})
	v.Update(client.StructuredEvent{
		EventType: "final",
		Data:      map[string]interface{}{},
	})

	// Should not panic and should return non-empty output
	out := v.View()
	if out == "" {
		t.Error("expected non-empty output after final event")
	}
}

// TestSwimlaneVizReAct verifies react_step events populate swimlane lanes.
func TestSwimlaneVizReAct(t *testing.T) {
	v := NewSwimlaneViz(80, 24)

	v.Update(client.StructuredEvent{
		EventType: "react_step",
		Data: map[string]interface{}{
			"step":        float64(1),
			"thought":     "I need to look this up",
			"action":      "web_search[query]",
			"observation": "Found relevant info",
		},
	})

	out := v.View()
	if !strings.Contains(out, "Thought") {
		t.Error("expected 'Thought' lane header in output")
	}
	if !strings.Contains(out, "Action") {
		t.Error("expected 'Action' lane header in output")
	}
	if !strings.Contains(out, "Observation") {
		t.Error("expected 'Observation' lane header in output")
	}
}

// TestDiffVizIterations verifies iteration events render with gauge.
func TestDiffVizIterations(t *testing.T) {
	v := NewDiffViz(80, 24)

	v.Update(client.StructuredEvent{
		EventType: "iteration",
		Data:      map[string]interface{}{"content": "Draft one content", "score": float64(0.6)},
	})
	v.Update(client.StructuredEvent{
		EventType: "iteration",
		Data:      map[string]interface{}{"content": "Improved draft content", "score": float64(0.85)},
	})
	v.Update(client.StructuredEvent{
		EventType: "refinement",
		Data:      map[string]interface{}{"content": "Final refined content", "score": float64(0.95)},
	})

	out := v.View()
	if !strings.Contains(out, "Iter 1") {
		t.Error("expected 'Iter 1' in diff output")
	}
	if !strings.Contains(out, "Iter 2") {
		t.Error("expected 'Iter 2' in diff output")
	}
	if !strings.Contains(out, "Iter 3") {
		t.Error("expected 'Iter 3' in diff output")
	}
}

// TestVotingVizSamples verifies sample events render columns.
func TestVotingVizSamples(t *testing.T) {
	v := NewVotingViz(80, 24)

	v.Update(client.StructuredEvent{
		EventType: "sample",
		Data:      map[string]interface{}{"id": float64(0), "content": "Sample one response", "answer": "42"},
	})
	v.Update(client.StructuredEvent{
		EventType: "sample",
		Data:      map[string]interface{}{"id": float64(1), "content": "Sample two response", "answer": "42"},
	})
	v.Update(client.StructuredEvent{
		EventType: "final",
		Data:      map[string]interface{}{"answer": "42"},
	})

	out := v.View()
	if !strings.Contains(out, "Sample 1") {
		t.Error("expected 'Sample 1' in voting output")
	}
	if !strings.Contains(out, "Winner") {
		t.Error("expected 'Winner' in voting output after final event")
	}
}

// TestPipelineVizStages verifies pipeline events render progress bar.
func TestPipelineVizStages(t *testing.T) {
	v := NewPipelineViz(80, 24)

	v.Update(client.StructuredEvent{
		EventType: "pipeline",
		Data: map[string]interface{}{
			"stage_name":   "Clarity",
			"stage_number": float64(1),
			"total_stages": float64(5),
			"content":      "Clarifying the problem",
			"score":        float64(0.8),
		},
	})

	out := v.View()
	if !strings.Contains(out, "Clarity") {
		t.Error("expected stage name 'Clarity' in pipeline output")
	}
}

// TestTaskTreeVizTasks verifies task events render with status icons.
func TestTaskTreeVizTasks(t *testing.T) {
	v := NewTaskTreeViz(80, 24)

	v.Update(client.StructuredEvent{
		EventType: "task",
		Data:      map[string]interface{}{"id": "t1", "description": "First subtask", "status": "pending"},
	})
	v.Update(client.StructuredEvent{
		EventType: "task",
		Data:      map[string]interface{}{"id": "t2", "description": "Second subtask", "status": "running"},
	})
	v.Update(client.StructuredEvent{
		EventType: "task",
		Data:      map[string]interface{}{"id": "t1", "description": "First subtask", "status": "completed", "result": "done"},
	})

	out := v.View()
	if !strings.Contains(out, "First subtask") {
		t.Error("expected 'First subtask' in task tree output")
	}
	if !strings.Contains(out, "Second subtask") {
		t.Error("expected 'Second subtask' in task tree output")
	}
}

// TestGetVisualizerReturnsCorrectType verifies registry returns the right types.
func TestGetVisualizerReturnsCorrectType(t *testing.T) {
	cases := map[string]bool{
		"cot":                true,
		"tot":                true,
		"react":              true,
		"consistency":        true,
		"reflection":         true,
		"refinement":         true,
		"complex_refinement": true,
		"debate":             true,
		"socratic":           true,
		"analogical":         true,
		"decomposed":         true,
		"least_to_most":      true,
		"standard":           false,
		"unknown":            false,
	}

	for agentID, expectNonNil := range cases {
		v := GetVisualizer(agentID, 80, 24)
		if expectNonNil && v == nil {
			t.Errorf("expected non-nil visualizer for %s", agentID)
		}
		if !expectNonNil && v != nil {
			t.Errorf("expected nil visualizer for %s, got non-nil", agentID)
		}
	}
}

// TestVisualizerReset verifies Reset clears state.
func TestVisualizerReset(t *testing.T) {
	v := NewStepsViz(80, 24)
	v.Update(client.StructuredEvent{
		EventType: "chain_step",
		Data:      map[string]interface{}{"step": float64(1), "content": "Some content"},
	})
	v.Reset()
	out := v.View()
	if strings.Contains(out, "Some content") {
		t.Error("expected content cleared after Reset")
	}
}

// TestSetSize verifies SetSize does not panic.
func TestSetSize(t *testing.T) {
	visualizers := []Visualizer{
		NewStepsViz(80, 24),
		NewTreeViz(80, 24),
		NewSwimlaneViz(80, 24),
		NewVotingViz(80, 24),
		NewDiffViz(80, 24),
		NewPipelineViz(80, 24),
		NewDebateViz(80, 24),
		NewSocraticViz(80, 24),
		NewAnalogyViz(80, 24),
		NewTaskTreeViz(80, 24),
	}
	for _, v := range visualizers {
		v.SetSize(120, 40)
		_ = v.View() // should not panic
	}
}
