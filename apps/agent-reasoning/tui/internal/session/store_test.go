package session

import (
	"testing"
	"time"
)

func TestSaveAndLoadSession(t *testing.T) {
	dir := t.TempDir()
	store := NewStore(dir)

	s := Session{
		ID:        "20260320_143022_tot",
		Timestamp: time.Date(2026, 3, 20, 14, 30, 22, 0, time.UTC),
		Type:      TypeChat,
		Model:     "gemma3:270m",
		Strategy:  "tot",
		Query:     "test query",
		Response:  "test response",
		Metrics: Metrics{
			TTFT_MS:    312,
			TotalMS:    2841,
			TPS:        42.3,
			TokenCount: 120,
		},
	}

	if err := store.Save(s); err != nil {
		t.Fatalf("save error: %v", err)
	}

	loaded, err := store.Load(s.ID)
	if err != nil {
		t.Fatalf("load error: %v", err)
	}
	if loaded.Query != "test query" {
		t.Errorf("expected 'test query', got '%s'", loaded.Query)
	}
	if loaded.Metrics.TPS != 42.3 {
		t.Errorf("expected TPS 42.3, got %f", loaded.Metrics.TPS)
	}
	if loaded.Type != TypeChat {
		t.Errorf("expected chat type, got %s", loaded.Type)
	}
}

func TestListSessions(t *testing.T) {
	dir := t.TempDir()
	store := NewStore(dir)

	ids := []string{"20260320_140000_cot", "20260320_150000_tot", "20260319_120000_react"}
	for _, id := range ids {
		store.Save(Session{ID: id, Type: TypeChat, Strategy: id[16:]})
	}

	sessions, err := store.List()
	if err != nil {
		t.Fatalf("list error: %v", err)
	}
	if len(sessions) != 3 {
		t.Errorf("expected 3, got %d", len(sessions))
	}
	// Newest first
	if sessions[0].ID != "20260320_150000_tot" {
		t.Errorf("expected newest first, got %s", sessions[0].ID)
	}
	if sessions[2].ID != "20260319_120000_react" {
		t.Errorf("expected oldest last, got %s", sessions[2].ID)
	}
}

func TestDeleteSession(t *testing.T) {
	dir := t.TempDir()
	store := NewStore(dir)
	store.Save(Session{ID: "test_session", Type: TypeChat})

	if err := store.Delete("test_session"); err != nil {
		t.Fatalf("delete error: %v", err)
	}

	_, err := store.Load("test_session")
	if err == nil {
		t.Error("expected error loading deleted session")
	}
}

func TestLoadNonexistent(t *testing.T) {
	dir := t.TempDir()
	store := NewStore(dir)

	_, err := store.Load("nonexistent")
	if err == nil {
		t.Error("expected error for nonexistent session")
	}
}

func TestGenerateID(t *testing.T) {
	id := GenerateID("tot")
	if len(id) < 10 {
		t.Error("expected non-trivial ID")
	}
}

func TestExportMarkdown(t *testing.T) {
	store := NewStore(t.TempDir())
	s := Session{
		ID:        "test",
		Timestamp: time.Date(2026, 3, 20, 14, 30, 0, 0, time.UTC),
		Type:      TypeChat,
		Model:     "gemma3:270m",
		Strategy:  "tot",
		Query:     "What is 2+2?",
		Response:  "The answer is 4.",
		Metrics:   Metrics{TTFT_MS: 100, TotalMS: 500, TPS: 30.0, TokenCount: 15},
	}

	md := store.ExportMarkdown(s)
	if len(md) == 0 {
		t.Error("expected non-empty markdown")
	}
	// Check key content
	if !contains(md, "gemma3:270m") {
		t.Error("expected model in markdown")
	}
	if !contains(md, "What is 2+2?") {
		t.Error("expected query in markdown")
	}
	if !contains(md, "30.0") {
		t.Error("expected TPS in markdown")
	}
}

func contains(s, substr string) bool {
	return len(s) >= len(substr) && searchString(s, substr)
}

func searchString(s, substr string) bool {
	for i := 0; i <= len(s)-len(substr); i++ {
		if s[i:i+len(substr)] == substr {
			return true
		}
	}
	return false
}

func TestSaveArenaSession(t *testing.T) {
	dir := t.TempDir()
	store := NewStore(dir)

	s := Session{
		ID:    "20260320_arena",
		Type:  TypeArena,
		Query: "test",
		ArenaResults: []ArenaResult{
			{AgentID: "cot", AgentName: "CoT", Response: "answer", Duration: 1.2, Tokens: 30, TPS: 25.0},
			{AgentID: "tot", AgentName: "ToT", Response: "answer2", Duration: 2.1, Tokens: 45, TPS: 21.4},
		},
	}

	if err := store.Save(s); err != nil {
		t.Fatalf("save error: %v", err)
	}

	loaded, err := store.Load(s.ID)
	if err != nil {
		t.Fatalf("load error: %v", err)
	}
	if len(loaded.ArenaResults) != 2 {
		t.Errorf("expected 2 arena results, got %d", len(loaded.ArenaResults))
	}
	if loaded.ArenaResults[0].AgentID != "cot" {
		t.Errorf("expected cot, got %s", loaded.ArenaResults[0].AgentID)
	}
}
