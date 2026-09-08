package web

import (
	"bufio"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	"github.com/jasperan/picooraclaw/pkg/agent"
	"github.com/jasperan/picooraclaw/pkg/bus"
	"github.com/jasperan/picooraclaw/pkg/config"
)

// Compile-time check that *Channel satisfies agent.EventEmitter.
var _ agent.EventEmitter = (*Channel)(nil)

func TestHandleEvents_StreamsSSE(t *testing.T) {
	cfg := config.WebConfig{Enabled: true, Host: "127.0.0.1", Port: 0}
	msgBus := bus.NewMessageBus()
	defer msgBus.Close()
	ch, err := NewChannel(cfg, msgBus)
	if err != nil {
		t.Fatal(err)
	}

	// httptest.NewServer + authMiddleware(muxForTest()) gives us a real listener.
	srv := httptest.NewServer(ch.authMiddleware(ch.muxForTest()))
	defer srv.Close()

	// Fire events asynchronously after the client is expected to be connected.
	go func() {
		time.Sleep(100 * time.Millisecond)
		ok := true
		ch.Emit(agent.Event{
			Type: agent.EventToolCallStart, SessionID: "s1", MessageID: "m1",
			ToolName: "remember", ToolCallID: "tc1", Timestamp: time.Now(),
		})
		ch.Emit(agent.Event{
			Type: agent.EventToolCallEnd, SessionID: "s1", MessageID: "m1",
			ToolCallID: "tc1", Result: "ok", OK: &ok, Timestamp: time.Now(),
		})
	}()

	ctx, cancel := context.WithTimeout(context.Background(), 3*time.Second)
	defer cancel()
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, srv.URL+"/v1/events?session_id=s1", nil)
	if err != nil {
		t.Fatal(err)
	}
	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		t.Fatal(err)
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		t.Fatalf("status = %d, want 200", resp.StatusCode)
	}

	// Read the SSE stream until we see both events (or time out via request ctx).
	scanner := bufio.NewScanner(resp.Body)
	var sb strings.Builder
	dataLines := 0
	deadline := time.Now().Add(2 * time.Second)
	for scanner.Scan() && time.Now().Before(deadline) {
		line := scanner.Text()
		sb.WriteString(line)
		sb.WriteString("\n")
		if strings.HasPrefix(line, "data:") {
			dataLines++
			if dataLines >= 2 {
				break
			}
		}
	}
	out := sb.String()
	if !strings.Contains(out, "tool_call_start") || !strings.Contains(out, "tool_call_end") {
		t.Fatalf("stream missing expected events; got:\n%s", out)
	}
}

func TestHandleChat_PublishesInboundToBus(t *testing.T) {
	msgBus := bus.NewMessageBus()
	defer msgBus.Close()

	cfg := config.WebConfig{Enabled: true, Host: "127.0.0.1", Port: 0}
	ch, err := NewChannel(cfg, msgBus)
	if err != nil {
		t.Fatal(err)
	}
	srv := httptest.NewServer(ch.authMiddleware(ch.muxForTest()))
	defer srv.Close()

	body := `{"session_id":"s1","text":"hello"}`
	resp, err := http.Post(srv.URL+"/v1/chat", "application/json", strings.NewReader(body))
	if err != nil {
		t.Fatal(err)
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusAccepted {
		t.Fatalf("want 202, got %d", resp.StatusCode)
	}

	ctx, cancel := context.WithTimeout(context.Background(), 500*time.Millisecond)
	defer cancel()
	msg, ok := msgBus.ConsumeInbound(ctx)
	if !ok {
		t.Fatal("expected inbound message on bus, got none")
	}
	if msg.Content != "hello" || msg.SessionKey != "s1" || msg.Channel != "web" {
		t.Fatalf("unexpected inbound: %+v", msg)
	}
	if _, has := msg.Metadata["workspace"]; has {
		t.Errorf("expected no workspace key in metadata, got %v", msg.Metadata)
	}
}

type fakeSessions struct{ items []SessionInfo }

func (f *fakeSessions) ListSessions() []SessionInfo { return f.items }

func (f *fakeSessions) CreateSession(t string) (SessionInfo, error) {
	s := SessionInfo{ID: "s_new", Title: t, LastAt: 1}
	f.items = append(f.items, s)
	return s, nil
}

func (f *fakeSessions) DeleteSession(id string) error {
	for i, s := range f.items {
		if s.ID == id {
			f.items = append(f.items[:i], f.items[i+1:]...)
			return nil
		}
	}
	return fmt.Errorf("not found")
}

func TestHandleSessions_ListCreateDelete(t *testing.T) {
	cfg := config.WebConfig{Enabled: true, Host: "127.0.0.1", Port: 0}
	msgBus := bus.NewMessageBus()
	defer msgBus.Close()
	ch, err := NewChannel(cfg, msgBus)
	if err != nil {
		t.Fatal(err)
	}
	f := &fakeSessions{items: []SessionInfo{{ID: "s1", Title: "one", LastAt: 10}}}
	ch.SetSessions(f)

	srv := httptest.NewServer(ch.authMiddleware(ch.muxForTest()))
	defer srv.Close()

	// GET
	resp, err := http.Get(srv.URL + "/v1/sessions")
	if err != nil {
		t.Fatal(err)
	}
	if resp.StatusCode != 200 {
		t.Fatalf("GET status %d", resp.StatusCode)
	}
	var got []SessionInfo
	_ = json.NewDecoder(resp.Body).Decode(&got)
	resp.Body.Close()
	if len(got) != 1 || got[0].ID != "s1" {
		t.Fatalf("list: %+v", got)
	}

	// POST
	resp, err = http.Post(srv.URL+"/v1/sessions", "application/json", strings.NewReader(`{"title":"two"}`))
	if err != nil {
		t.Fatal(err)
	}
	if resp.StatusCode != 201 {
		t.Fatalf("POST status %d", resp.StatusCode)
	}
	resp.Body.Close()

	// DELETE
	req, _ := http.NewRequest(http.MethodDelete, srv.URL+"/v1/sessions?id=s1", nil)
	resp, err = http.DefaultClient.Do(req)
	if err != nil {
		t.Fatal(err)
	}
	if resp.StatusCode != 204 {
		t.Fatalf("DELETE status %d", resp.StatusCode)
	}
	resp.Body.Close()
}

func TestHandleSessions_NoBackend_GetReturnsEmptyArray(t *testing.T) {
	cfg := config.WebConfig{Enabled: true, Host: "127.0.0.1", Port: 0}
	msgBus := bus.NewMessageBus()
	defer msgBus.Close()
	ch, err := NewChannel(cfg, msgBus)
	if err != nil {
		t.Fatal(err)
	}
	// no SetSessions — sessions is nil

	srv := httptest.NewServer(ch.authMiddleware(ch.muxForTest()))
	defer srv.Close()

	resp, err := http.Get(srv.URL + "/v1/sessions")
	if err != nil {
		t.Fatal(err)
	}
	defer resp.Body.Close()
	if resp.StatusCode != 200 {
		t.Fatalf("want 200, got %d", resp.StatusCode)
	}
	body, _ := io.ReadAll(resp.Body)
	if strings.TrimSpace(string(body)) != "[]" {
		t.Fatalf("want empty JSON array, got: %q", string(body))
	}
}

func TestHandleSessions_DeleteMissingID_Returns400(t *testing.T) {
	cfg := config.WebConfig{Enabled: true, Host: "127.0.0.1", Port: 0}
	msgBus := bus.NewMessageBus()
	defer msgBus.Close()
	ch, err := NewChannel(cfg, msgBus)
	if err != nil {
		t.Fatal(err)
	}
	ch.SetSessions(&fakeSessions{})

	srv := httptest.NewServer(ch.authMiddleware(ch.muxForTest()))
	defer srv.Close()

	req, _ := http.NewRequest(http.MethodDelete, srv.URL+"/v1/sessions", nil)
	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		t.Fatal(err)
	}
	resp.Body.Close()
	if resp.StatusCode != 400 {
		t.Fatalf("want 400, got %d", resp.StatusCode)
	}
}

func TestHandleSessions_PostEmptyTitle_Returns400(t *testing.T) {
	cfg := config.WebConfig{Enabled: true, Host: "127.0.0.1", Port: 0}
	msgBus := bus.NewMessageBus()
	defer msgBus.Close()
	ch, err := NewChannel(cfg, msgBus)
	if err != nil {
		t.Fatal(err)
	}
	ch.SetSessions(&fakeSessions{})

	srv := httptest.NewServer(ch.authMiddleware(ch.muxForTest()))
	defer srv.Close()

	resp, err := http.Post(srv.URL+"/v1/sessions", "application/json", strings.NewReader(`{"title":""}`))
	if err != nil {
		t.Fatal(err)
	}
	resp.Body.Close()
	if resp.StatusCode != 400 {
		t.Fatalf("want 400, got %d", resp.StatusCode)
	}
}

func TestHandleSessions_PostMalformedJSON_Returns400(t *testing.T) {
	cfg := config.WebConfig{Enabled: true, Host: "127.0.0.1", Port: 0}
	msgBus := bus.NewMessageBus()
	defer msgBus.Close()
	ch, err := NewChannel(cfg, msgBus)
	if err != nil {
		t.Fatal(err)
	}
	ch.SetSessions(&fakeSessions{})

	srv := httptest.NewServer(ch.authMiddleware(ch.muxForTest()))
	defer srv.Close()

	resp, err := http.Post(srv.URL+"/v1/sessions", "application/json", strings.NewReader(`{`))
	if err != nil {
		t.Fatal(err)
	}
	resp.Body.Close()
	if resp.StatusCode != 400 {
		t.Fatalf("want 400, got %d", resp.StatusCode)
	}
}

type fakeMemory struct{}

func (fakeMemory) Search(q string, n int) []MemoryResult {
	return []MemoryResult{{ID: "m_1", Text: "user likes " + q, Score: 0.9, Date: 1}}
}

func TestHandleMemory_Search(t *testing.T) {
	cfg := config.WebConfig{Enabled: true, Host: "127.0.0.1", Port: 0}
	msgBus := bus.NewMessageBus()
	defer msgBus.Close()
	ch, err := NewChannel(cfg, msgBus)
	if err != nil {
		t.Fatal(err)
	}
	ch.SetMemory(fakeMemory{})

	srv := httptest.NewServer(ch.authMiddleware(ch.muxForTest()))
	defer srv.Close()

	resp, err := http.Get(srv.URL + "/v1/memory?q=go&limit=5")
	if err != nil {
		t.Fatal(err)
	}
	defer resp.Body.Close()
	if resp.StatusCode != 200 {
		t.Fatalf("status %d", resp.StatusCode)
	}
	var got []MemoryResult
	_ = json.NewDecoder(resp.Body).Decode(&got)
	if len(got) != 1 || !strings.Contains(got[0].Text, "go") {
		t.Fatalf("unexpected: %+v", got)
	}
}

func TestHandleMemory_NoBackendReturnsEmptyArray(t *testing.T) {
	cfg := config.WebConfig{Enabled: true, Host: "127.0.0.1", Port: 0}
	msgBus := bus.NewMessageBus()
	defer msgBus.Close()
	ch, err := NewChannel(cfg, msgBus)
	if err != nil {
		t.Fatal(err)
	}
	// no SetMemory

	srv := httptest.NewServer(ch.authMiddleware(ch.muxForTest()))
	defer srv.Close()

	resp, err := http.Get(srv.URL + "/v1/memory?q=anything")
	if err != nil {
		t.Fatal(err)
	}
	defer resp.Body.Close()
	body, _ := io.ReadAll(resp.Body)
	if strings.TrimSpace(string(body)) != "[]" {
		t.Fatalf("expected [], got %q", string(body))
	}
}

func TestHandleMemory_MethodNotAllowed(t *testing.T) {
	cfg := config.WebConfig{Enabled: true, Host: "127.0.0.1", Port: 0}
	msgBus := bus.NewMessageBus()
	defer msgBus.Close()
	ch, err := NewChannel(cfg, msgBus)
	if err != nil {
		t.Fatal(err)
	}

	srv := httptest.NewServer(ch.authMiddleware(ch.muxForTest()))
	defer srv.Close()

	resp, err := http.Post(srv.URL+"/v1/memory", "application/json", strings.NewReader("{}"))
	if err != nil {
		t.Fatal(err)
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusMethodNotAllowed {
		t.Fatalf("expected 405, got %d", resp.StatusCode)
	}
}

func TestHandleMemory_BadLimitFallsBackToDefault(t *testing.T) {
	cfg := config.WebConfig{Enabled: true, Host: "127.0.0.1", Port: 0}
	msgBus := bus.NewMessageBus()
	defer msgBus.Close()
	ch, err := NewChannel(cfg, msgBus)
	if err != nil {
		t.Fatal(err)
	}
	ch.SetMemory(fakeMemory{})

	srv := httptest.NewServer(ch.authMiddleware(ch.muxForTest()))
	defer srv.Close()

	// garbage limit should not 500 — falls back to default
	resp, err := http.Get(srv.URL + "/v1/memory?q=x&limit=not-a-number")
	if err != nil {
		t.Fatal(err)
	}
	defer resp.Body.Close()
	if resp.StatusCode != 200 {
		t.Fatalf("status %d", resp.StatusCode)
	}
}

func TestHandleMemory_NilResultsReturnsEmptyArray(t *testing.T) {
	cfg := config.WebConfig{Enabled: true, Host: "127.0.0.1", Port: 0}
	msgBus := bus.NewMessageBus()
	defer msgBus.Close()
	ch, err := NewChannel(cfg, msgBus)
	if err != nil {
		t.Fatal(err)
	}
	ch.SetMemory(nilMemory{})

	srv := httptest.NewServer(ch.authMiddleware(ch.muxForTest()))
	defer srv.Close()

	resp, err := http.Get(srv.URL + "/v1/memory?q=x")
	if err != nil {
		t.Fatal(err)
	}
	defer resp.Body.Close()
	body, _ := io.ReadAll(resp.Body)
	if strings.TrimSpace(string(body)) != "[]" {
		t.Fatalf("expected [], got %q", string(body))
	}
}

type nilMemory struct{}

func (nilMemory) Search(q string, n int) []MemoryResult { return nil }

func TestAuthMiddleware_RejectsWrongToken(t *testing.T) {
	cfg := config.WebConfig{Enabled: true, Host: "127.0.0.1", Port: 0, Token: "secret"}
	msgBus := bus.NewMessageBus()
	defer msgBus.Close()
	ch, _ := NewChannel(cfg, msgBus)
	srv := httptest.NewServer(ch.authMiddleware(ch.muxForTest()))
	defer srv.Close()

	// No header → 401
	resp, err := http.Get(srv.URL + "/v1/sessions")
	if err != nil {
		t.Fatal(err)
	}
	resp.Body.Close()
	if resp.StatusCode != http.StatusUnauthorized {
		t.Fatalf("no-auth status %d, want 401", resp.StatusCode)
	}

	// Wrong header → 401
	req, _ := http.NewRequest(http.MethodGet, srv.URL+"/v1/sessions", nil)
	req.Header.Set("Authorization", "Bearer nope")
	resp, err = http.DefaultClient.Do(req)
	if err != nil {
		t.Fatal(err)
	}
	resp.Body.Close()
	if resp.StatusCode != http.StatusUnauthorized {
		t.Fatalf("wrong-token status %d, want 401", resp.StatusCode)
	}

	// Correct header → 200 (handleSessions returns [] when no backend)
	req, _ = http.NewRequest(http.MethodGet, srv.URL+"/v1/sessions", nil)
	req.Header.Set("Authorization", "Bearer secret")
	resp, err = http.DefaultClient.Do(req)
	if err != nil {
		t.Fatal(err)
	}
	resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		t.Fatalf("correct-token status %d, want 200", resp.StatusCode)
	}
}
