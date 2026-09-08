package ui

import (
	"strings"
	"testing"
	"time"
)

func TestMetricsBarInactive(t *testing.T) {
	m := NewMetricsBar()
	if m.View() != "" {
		t.Error("inactive bar should render empty")
	}
}

func TestMetricsBarActive(t *testing.T) {
	m := NewMetricsBar()
	m.SetWidth(100)
	m.SetTTFT(312 * time.Millisecond)
	m.SetTokens(120)
	m.SetTPS(42.3)
	m.SetDuration(2841 * time.Millisecond)
	m.SetModel("gemma3:270m")

	view := m.View()
	if !strings.Contains(view, "312ms") {
		t.Error("expected TTFT in view")
	}
	if !strings.Contains(view, "120") {
		t.Error("expected token count in view")
	}
	if !strings.Contains(view, "42.3") {
		t.Error("expected TPS in view")
	}
	if !strings.Contains(view, "2.8s") {
		t.Error("expected duration in view")
	}
	if !strings.Contains(view, "gemma3:270m") {
		t.Error("expected model in view")
	}
}

func TestMetricsBarReset(t *testing.T) {
	m := NewMetricsBar()
	m.SetTTFT(100 * time.Millisecond)
	m.Reset()
	if m.View() != "" {
		t.Error("reset bar should render empty")
	}
}

func TestTPSTier(t *testing.T) {
	tests := []struct {
		tps      float64
		expected string
	}{
		{35.0, "green"},
		{15.0, "yellow"},
		{5.0, "red"},
		{30.1, "green"},
		{10.1, "yellow"},
		{0.0, "red"},
	}
	for _, tc := range tests {
		got := TPSTier(tc.tps)
		if got != tc.expected {
			t.Errorf("TPSTier(%.1f) = %s, want %s", tc.tps, got, tc.expected)
		}
	}
}
