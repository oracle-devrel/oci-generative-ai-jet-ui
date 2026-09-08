package ui

import (
	"strings"
	"testing"
)

func TestSparklineEmpty(t *testing.T) {
	s := NewSparkline(10)
	view := s.View()
	// Should return something of visual width 10 (spaces)
	if lipglossWidth(view) != 10 {
		t.Errorf("empty sparkline width: got %d want 10", lipglossWidth(view))
	}
}

func TestSparklinePushAndView(t *testing.T) {
	s := NewSparkline(5)
	s.Push(0.0)
	s.Push(0.5)
	s.Push(1.0)
	view := s.View()
	if lipglossWidth(view) != 5 {
		t.Errorf("sparkline width: got %d want 5", lipglossWidth(view))
	}
	// Should contain block chars
	stripped := stripAnsi(view)
	hasBlock := false
	for _, r := range []rune(stripped) {
		for _, c := range sparkChars {
			if r == c {
				hasBlock = true
			}
		}
	}
	if !hasBlock {
		t.Errorf("expected block characters in sparkline view")
	}
}

func TestSparklineTrimToWidth(t *testing.T) {
	s := NewSparkline(3)
	for i := 0; i < 10; i++ {
		s.Push(float64(i) / 9.0)
	}
	if len(s.values) > 3 {
		t.Errorf("values not trimmed: got %d want <= 3", len(s.values))
	}
	view := s.View()
	if lipglossWidth(view) != 3 {
		t.Errorf("view width after trim: got %d want 3", lipglossWidth(view))
	}
}

func TestSparklineNormalizedView(t *testing.T) {
	s := NewSparkline(8)
	s.Push(10.0)
	s.Push(20.0)
	s.Push(30.0)
	view := s.NormalizedView()
	if lipglossWidth(view) != 8 {
		t.Errorf("normalized view width: got %d want 8", lipglossWidth(view))
	}
	stripped := stripAnsi(view)
	// Last char should be highest block
	runes := []rune(strings.TrimRight(stripped, " "))
	if len(runes) == 0 {
		t.Fatal("no runes in normalized view")
	}
	last := runes[len(runes)-1]
	if last != '█' {
		t.Errorf("last char should be █ (max), got %c", last)
	}
}

func TestSparklineNormalizedUniform(t *testing.T) {
	s := NewSparkline(4)
	s.Push(5.0)
	s.Push(5.0)
	s.Push(5.0)
	// Should not panic with zero range
	view := s.NormalizedView()
	if lipglossWidth(view) != 4 {
		t.Errorf("uniform normalized width: got %d want 4", lipglossWidth(view))
	}
}

// helpers

func lipglossWidth(s string) int {
	return len([]rune(stripAnsi(s)))
}

func stripAnsi(s string) string {
	return ansiStrip(s)
}
