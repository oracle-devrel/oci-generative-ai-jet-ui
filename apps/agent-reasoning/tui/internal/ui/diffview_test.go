package ui

import (
	"strings"
	"testing"
)

func TestDiffViewEmpty(t *testing.T) {
	d := NewDiffView(80, 20)
	if d.View() != "" {
		t.Errorf("empty DiffView should return empty string")
	}
}

func TestDiffViewAddIteration(t *testing.T) {
	d := NewDiffView(80, 20)
	d.AddIteration("First draft content", 0.5)
	view := d.View()
	raw := stripAnsi(view)
	if !strings.Contains(raw, "Iter 1:") {
		t.Errorf("view should contain 'Iter 1:'")
	}
	if !strings.Contains(raw, "First draft content") {
		t.Errorf("view should contain iteration content")
	}
	if !strings.Contains(raw, "0.50") {
		t.Errorf("view should contain score")
	}
}

func TestDiffViewMultipleIterations(t *testing.T) {
	d := NewDiffView(80, 30)
	d.AddIteration("Draft 1", 0.4)
	d.AddIteration("Draft 2", 0.7)
	d.AddIteration("Draft 3", 0.95)
	view := d.View()
	raw := stripAnsi(view)
	for i := 1; i <= 3; i++ {
		label := "Iter " + string(rune('0'+i)) + ":"
		if !strings.Contains(raw, label) {
			t.Errorf("expected %q in view", label)
		}
	}
	// Should have separator lines between iterations
	if !strings.Contains(raw, "─") {
		t.Errorf("expected separator ─ between iterations")
	}
}

func TestDiffViewGaugeContainsBlocks(t *testing.T) {
	d := NewDiffView(80, 20)
	d.SetThreshold(0.8)
	d.AddIteration("content", 0.6)
	view := d.View()
	raw := stripAnsi(view)
	// Gauge chars: filled ██ or empty ░
	if !strings.ContainsAny(raw, "█░") {
		t.Errorf("gauge should contain block characters")
	}
}

func TestDiffViewThresholdMarker(t *testing.T) {
	d := NewDiffView(80, 20)
	d.SetThreshold(0.5)
	d.AddIteration("test", 0.3)
	view := d.View()
	raw := stripAnsi(view)
	if !strings.Contains(raw, "│") {
		t.Errorf("gauge should contain │ threshold marker")
	}
}
