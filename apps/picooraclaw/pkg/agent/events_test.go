package agent

import (
	"testing"
	"time"
)

func TestEvent_JSON(t *testing.T) {
	e := Event{
		Type:      EventToolCallStart,
		SessionID: "s1",
		MessageID: "m1",
		ToolName:  "remember",
		Args:      map[string]any{"text": "hi"},
		Timestamp: time.Unix(1000, 0),
	}
	if e.Type != "tool_call_start" {
		t.Fatalf("unexpected type: %q", e.Type)
	}
}

type captureEmitter struct{ events []Event }

func (c *captureEmitter) Emit(e Event) { c.events = append(c.events, e) }

func TestCaptureEmitter_Interface(t *testing.T) {
	var _ EventEmitter = (*captureEmitter)(nil)
}
