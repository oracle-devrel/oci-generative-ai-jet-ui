package web

import (
	"bufio"
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	"github.com/jasperan/picooraclaw/pkg/agent"
	"github.com/jasperan/picooraclaw/pkg/bus"
	"github.com/jasperan/picooraclaw/pkg/config"
)

func TestE2E_ChatThenEventStream(t *testing.T) {
	msgBus := bus.NewMessageBus()
	defer msgBus.Close()

	cfg := config.WebConfig{Enabled: true, Host: "127.0.0.1", Port: 0}
	ch, err := NewChannel(cfg, msgBus)
	if err != nil {
		t.Fatal(err)
	}
	srv := httptest.NewServer(ch.authMiddleware(ch.muxForTest()))
	defer srv.Close()

	// Fake agent: consume inbound bus message, emit 4 events back through the channel.
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	go func() {
		msg, ok := msgBus.ConsumeInbound(ctx)
		if !ok {
			return
		}
		okTrue := true
		ch.Emit(agent.Event{Type: agent.EventMessageStart, SessionID: msg.SessionKey, MessageID: "m1", Timestamp: time.Now()})
		ch.Emit(agent.Event{Type: agent.EventToolCallStart, SessionID: msg.SessionKey, MessageID: "m1", ToolCallID: "tc1", ToolName: "remember", Timestamp: time.Now()})
		ch.Emit(agent.Event{Type: agent.EventToolCallEnd, SessionID: msg.SessionKey, MessageID: "m1", ToolCallID: "tc1", ToolName: "remember", OK: &okTrue, Result: "stored", Timestamp: time.Now()})
		ch.Emit(agent.Event{Type: agent.EventMessageEnd, SessionID: msg.SessionKey, MessageID: "m1", Text: "done", Timestamp: time.Now()})
	}()

	// Open SSE FIRST so the subscription exists before events arrive.
	resp, err := http.Get(srv.URL + "/v1/events?session_id=s_e2e")
	if err != nil {
		t.Fatal(err)
	}
	defer resp.Body.Close()

	// Post chat asynchronously; the fake agent goroutine will consume + emit.
	go func() {
		_, _ = http.Post(srv.URL+"/v1/chat", "application/json", strings.NewReader(`{"session_id":"s_e2e","text":"hi"}`))
	}()

	// Read 4 SSE data events.
	scanner := bufio.NewScanner(resp.Body)
	scanner.Buffer(make([]byte, 0, 64*1024), 1<<20)
	deadline := time.Now().Add(3 * time.Second)
	got := 0
	types := []string{}
	for scanner.Scan() {
		if time.Now().After(deadline) {
			t.Fatalf("timeout; types=%v", types)
		}
		line := scanner.Text()
		if !strings.HasPrefix(line, "data:") {
			continue
		}
		var ev Event
		if err := json.Unmarshal([]byte(strings.TrimPrefix(line, "data: ")), &ev); err != nil {
			t.Fatalf("unmarshal: %v; line=%q", err, line)
		}
		types = append(types, ev.Type)
		got++
		if got == 4 {
			break
		}
	}
	want := []string{"message_start", "tool_call_start", "tool_call_end", "message_end"}
	if strings.Join(types, ",") != strings.Join(want, ",") {
		t.Fatalf("want %v, got %v", want, types)
	}
}
