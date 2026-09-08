package ui

import (
	"strings"
	"testing"
)

func TestSwimlaneHeaders(t *testing.T) {
	lanes := []LaneConfig{
		{Name: "Thought", Color: "#00FFFF"},
		{Name: "Action", Color: "#FFFF00"},
		{Name: "Observe", Color: "#00FF00"},
	}
	sw := NewSwimlane(60, 20, lanes)
	view := sw.View()
	raw := stripAnsi(view)
	for _, lane := range lanes {
		if !strings.Contains(raw, lane.Name) {
			t.Errorf("header should contain lane name %q", lane.Name)
		}
	}
	if !strings.Contains(raw, "│") {
		t.Errorf("header should contain │ separator")
	}
}

func TestSwimlaneRowPlacement(t *testing.T) {
	lanes := []LaneConfig{
		{Name: "A", Color: "#00FFFF"},
		{Name: "B", Color: "#FFFF00"},
		{Name: "C", Color: "#00FF00"},
	}
	sw := NewSwimlane(60, 20, lanes)
	sw.AddRow(0, "alpha")
	sw.AddRow(1, "beta")
	sw.AddRow(2, "gamma")
	view := sw.View()
	raw := stripAnsi(view)
	if !strings.Contains(raw, "alpha") {
		t.Errorf("row content 'alpha' missing")
	}
	if !strings.Contains(raw, "beta") {
		t.Errorf("row content 'beta' missing")
	}
	if !strings.Contains(raw, "gamma") {
		t.Errorf("row content 'gamma' missing")
	}
}

func TestSwimlaneInvalidLane(t *testing.T) {
	lanes := []LaneConfig{
		{Name: "A", Color: "#00FFFF"},
	}
	sw := NewSwimlane(40, 10, lanes)
	// Should not panic on invalid lane index
	sw.AddRow(-1, "bad")
	sw.AddRow(5, "also bad")
	view := sw.View()
	raw := stripAnsi(view)
	if strings.Contains(raw, "bad") {
		t.Errorf("invalid lane content should not appear")
	}
}

func TestSwimlaneHeightTruncation(t *testing.T) {
	lanes := []LaneConfig{
		{Name: "Only", Color: "#00FFFF"},
	}
	sw := NewSwimlane(30, 4, lanes) // height=4: 2 header + 2 data rows
	for i := 0; i < 10; i++ {
		sw.AddRow(0, "row")
	}
	view := sw.View()
	lines := strings.Split(view, "\n")
	if len(lines) > 4 {
		t.Errorf("swimlane exceeded height: got %d lines, want <= 4", len(lines))
	}
}

func TestSwimlaneEmpty(t *testing.T) {
	lanes := []LaneConfig{
		{Name: "X", Color: "#00FFFF"},
		{Name: "Y", Color: "#FFFF00"},
	}
	sw := NewSwimlane(40, 10, lanes)
	view := sw.View()
	if !strings.Contains(stripAnsi(view), "X") {
		t.Errorf("empty swimlane should still show headers")
	}
}
