package ui

import (
	"strings"
	"testing"
)

func TestProgressBarBasic(t *testing.T) {
	stages := []string{"Parse", "Think", "Draft", "Refine", "Done"}
	p := NewProgressBar(stages, 60)
	p.SetCurrent(1)
	view := p.View()
	raw := stripAnsi(view)
	if !strings.Contains(raw, "Stage 2/5") {
		t.Errorf("expected 'Stage 2/5', got: %s", raw)
	}
	if !strings.Contains(raw, "Think") {
		t.Errorf("expected stage name 'Think', got: %s", raw)
	}
}

func TestProgressBarFirstStage(t *testing.T) {
	stages := []string{"Start", "Middle", "End"}
	p := NewProgressBar(stages, 50)
	p.SetCurrent(0)
	view := p.View()
	raw := stripAnsi(view)
	if !strings.Contains(raw, "Stage 1/3") {
		t.Errorf("expected 'Stage 1/3', got: %s", raw)
	}
	if !strings.Contains(raw, "Start") {
		t.Errorf("expected stage name 'Start'")
	}
}

func TestProgressBarLastStage(t *testing.T) {
	stages := []string{"Alpha", "Beta", "Gamma"}
	p := NewProgressBar(stages, 50)
	p.SetCurrent(2)
	view := p.View()
	raw := stripAnsi(view)
	if !strings.Contains(raw, "Stage 3/3") {
		t.Errorf("expected 'Stage 3/3', got: %s", raw)
	}
	if !strings.Contains(raw, "Gamma") {
		t.Errorf("expected stage name 'Gamma'")
	}
}

func TestProgressBarHasBlocks(t *testing.T) {
	stages := []string{"A", "B", "C", "D"}
	p := NewProgressBar(stages, 60)
	p.SetCurrent(2)
	view := p.View()
	raw := stripAnsi(view)
	if !strings.ContainsAny(raw, "█░") {
		t.Errorf("progress bar should contain block characters")
	}
	if !strings.Contains(raw, "[") || !strings.Contains(raw, "]") {
		t.Errorf("progress bar should have brackets")
	}
}

func TestProgressBarEmpty(t *testing.T) {
	p := NewProgressBar([]string{}, 50)
	view := p.View()
	if view != "" {
		t.Errorf("empty stages should produce empty string")
	}
}
