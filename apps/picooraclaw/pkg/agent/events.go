package agent

import "time"

type EventType string

const (
	EventMessageStart  EventType = "message_start"
	EventMessageEnd    EventType = "message_end"
	EventToolCallStart EventType = "tool_call_start"
	EventToolCallEnd   EventType = "tool_call_end"
	EventError         EventType = "error"
	EventAgentTick     EventType = "agent_tick"
)

type Event struct {
	Type       EventType      `json:"type"`
	SessionID  string         `json:"session_id"`
	MessageID  string         `json:"message_id,omitempty"`
	ToolName   string         `json:"tool,omitempty"`
	ToolCallID string         `json:"id,omitempty"`
	Args       map[string]any `json:"args,omitempty"`
	Result     string         `json:"result,omitempty"`
	OK         *bool          `json:"ok,omitempty"`
	Text       string         `json:"text,omitempty"`
	Error      string         `json:"error,omitempty"`
	Note       string         `json:"note,omitempty"`
	Timestamp  time.Time      `json:"ts"`
}

type EventEmitter interface {
	Emit(e Event)
}

type NoopEmitter struct{}

func (NoopEmitter) Emit(Event) {}
