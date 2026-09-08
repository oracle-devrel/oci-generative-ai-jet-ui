package client

import (
	"encoding/json"
	"testing"
)

func TestParseAgentsResponse(t *testing.T) {
	raw := `{"agents":[{"id":"tot","name":"Tree of Thoughts","description":"test","reference":"Yao","best_for":"puzzles","tradeoffs":"+good","has_visualizer":true,"parameters":{"width":{"type":"int","default":2,"min":1,"max":5,"description":"Branching factor"}}}],"count":1}`

	var resp AgentsResponse
	if err := json.Unmarshal([]byte(raw), &resp); err != nil {
		t.Fatalf("unmarshal error: %v", err)
	}
	if len(resp.Agents) != 1 {
		t.Fatalf("expected 1 agent, got %d", len(resp.Agents))
	}
	a := resp.Agents[0]
	if a.ID != "tot" {
		t.Errorf("expected tot, got %s", a.ID)
	}
	if !a.HasVisualizer {
		t.Error("expected has_visualizer true")
	}
	if a.Parameters["width"].Default != 2 {
		t.Errorf("expected width default 2, got %f", a.Parameters["width"].Default)
	}
}

func TestParseAgentsResponseEmpty(t *testing.T) {
	raw := `{"agents":[],"count":0}`
	var resp AgentsResponse
	if err := json.Unmarshal([]byte(raw), &resp); err != nil {
		t.Fatalf("unmarshal error: %v", err)
	}
	if len(resp.Agents) != 0 {
		t.Error("expected empty agents")
	}
}

func TestParseStructuredEvent(t *testing.T) {
	raw := `{"event_type":"node","data":{"id":"root","content":"test","score":0.85},"is_update":false}`
	var event StructuredEvent
	if err := json.Unmarshal([]byte(raw), &event); err != nil {
		t.Fatalf("unmarshal error: %v", err)
	}
	if event.EventType != "node" {
		t.Errorf("expected node, got %s", event.EventType)
	}
	if event.IsUpdate {
		t.Error("expected is_update false")
	}
	if event.Data["id"] != "root" {
		t.Errorf("expected root, got %v", event.Data["id"])
	}
}

func TestParseStructuredEventText(t *testing.T) {
	raw := `{"event_type":"text","data":{"content":"hello"},"is_update":false}`
	var event StructuredEvent
	if err := json.Unmarshal([]byte(raw), &event); err != nil {
		t.Fatalf("unmarshal error: %v", err)
	}
	if event.EventType != "text" {
		t.Errorf("expected text, got %s", event.EventType)
	}
	if event.Data["content"] != "hello" {
		t.Errorf("expected hello, got %v", event.Data["content"])
	}
}

func TestParseStructuredEventDone(t *testing.T) {
	raw := `{"event_type":"done","data":{},"is_update":false}`
	var event StructuredEvent
	if err := json.Unmarshal([]byte(raw), &event); err != nil {
		t.Fatalf("unmarshal error: %v", err)
	}
	if event.EventType != "done" {
		t.Errorf("expected done, got %s", event.EventType)
	}
}
