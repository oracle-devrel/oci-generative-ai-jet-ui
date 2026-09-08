package ui

import (
	"strings"
	"testing"
)

func TestTreeGraphSingleNode(t *testing.T) {
	root := &TreeGraphNode{Label: "Root", Status: NodeDone, Score: 0.9}
	g := NewTreeGraph(root, 80, 20)
	view := g.View()
	if !strings.Contains(stripAnsi(view), "Root") {
		t.Errorf("single node view should contain label 'Root'")
	}
	if !strings.Contains(stripAnsi(view), "✓") {
		t.Errorf("done node should show ✓ icon")
	}
	if !strings.Contains(stripAnsi(view), "0.90") {
		t.Errorf("score should appear in view")
	}
}

func TestTreeGraphWithChildren(t *testing.T) {
	root := &TreeGraphNode{
		Label:  "Root",
		Status: NodeActive,
		Children: []*TreeGraphNode{
			{Label: "Child A", Status: NodeDone},
			{Label: "Child B", Status: NodePruned},
		},
	}
	g := NewTreeGraph(root, 80, 20)
	view := g.View()
	raw := stripAnsi(view)
	if !strings.Contains(raw, "Child A") {
		t.Errorf("view should contain Child A")
	}
	if !strings.Contains(raw, "Child B") {
		t.Errorf("view should contain Child B")
	}
	if !strings.Contains(raw, "└──") {
		t.Errorf("last child should use └──")
	}
	if !strings.Contains(raw, "├──") {
		t.Errorf("non-last child should use ├──")
	}
}

func TestTreeGraphHighlightPath(t *testing.T) {
	child := &TreeGraphNode{Label: "Target", Status: NodeDone}
	root := &TreeGraphNode{
		Label:    "Root",
		Status:   NodeActive,
		Children: []*TreeGraphNode{child},
	}
	g := NewTreeGraph(root, 80, 20)
	g.HighlightPath(child)
	if !root.Highlighted {
		t.Errorf("root should be highlighted when target is a child")
	}
	if !child.Highlighted {
		t.Errorf("target should be highlighted")
	}
}

func TestTreeGraphTruncation(t *testing.T) {
	children := make([]*TreeGraphNode, 10)
	for i := range children {
		children[i] = &TreeGraphNode{Label: "Node", Status: NodePending}
	}
	root := &TreeGraphNode{Label: "Root", Status: NodeActive, Children: children}
	g := NewTreeGraph(root, 80, 5)
	view := g.View()
	lines := strings.Split(view, "\n")
	// Should have at most height+1 lines (truncated line appended)
	if len(lines) > 6 {
		t.Errorf("truncated view has too many lines: got %d", len(lines))
	}
	if !strings.Contains(stripAnsi(view), "truncated") {
		t.Errorf("truncated view should say 'truncated'")
	}
}

func TestTreeGraphNilRoot(t *testing.T) {
	g := NewTreeGraph(nil, 80, 20)
	view := g.View()
	if view != "" {
		t.Errorf("nil root should produce empty string")
	}
}
