package session

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"time"
)

type SessionType string

const (
	TypeChat  SessionType = "chat"
	TypeArena SessionType = "arena"
	TypeDuel  SessionType = "duel"
	TypeDebug SessionType = "debug"
)

type Metrics struct {
	TTFT_MS    float64 `json:"ttft_ms"`
	TotalMS    float64 `json:"total_ms"`
	TPS        float64 `json:"tps"`
	TokenCount int     `json:"token_count"`
}

type ArenaResult struct {
	AgentID   string  `json:"agent_id"`
	AgentName string  `json:"agent_name"`
	Response  string  `json:"response"`
	Duration  float64 `json:"duration"`
	Tokens    int     `json:"tokens"`
	TPS       float64 `json:"tps"`
	Error     string  `json:"error,omitempty"`
}

type DuelResult struct {
	LeftAgent     string  `json:"left_agent"`
	RightAgent    string  `json:"right_agent"`
	LeftResponse  string  `json:"left_response"`
	RightResponse string  `json:"right_response"`
	LeftMetrics   Metrics `json:"left_metrics"`
	RightMetrics  Metrics `json:"right_metrics"`
	Judgment      string  `json:"judgment,omitempty"`
}

type Session struct {
	ID           string        `json:"id"`
	Timestamp    time.Time     `json:"timestamp"`
	Type         SessionType   `json:"type"`
	Model        string        `json:"model"`
	Strategy     string        `json:"strategy"`
	Query        string        `json:"query"`
	Response     string        `json:"response,omitempty"`
	Metrics      Metrics       `json:"metrics,omitempty"`
	ArenaResults []ArenaResult `json:"arena_results,omitempty"`
	DuelResult   *DuelResult   `json:"duel_result,omitempty"`
}

type Store struct {
	dir string
}

func NewStore(dir string) *Store {
	os.MkdirAll(dir, 0755)
	return &Store{dir: dir}
}

func GenerateID(strategy string) string {
	return fmt.Sprintf("%s_%s", time.Now().Format("20060102_150405"), strategy)
}

func (s *Store) Save(session Session) error {
	if session.Timestamp.IsZero() {
		session.Timestamp = time.Now()
	}
	data, err := json.MarshalIndent(session, "", "  ")
	if err != nil {
		return err
	}
	path := filepath.Join(s.dir, session.ID+".json")
	return os.WriteFile(path, data, 0644)
}

func (s *Store) Load(id string) (Session, error) {
	path := filepath.Join(s.dir, id+".json")
	data, err := os.ReadFile(path)
	if err != nil {
		return Session{}, err
	}
	var session Session
	err = json.Unmarshal(data, &session)
	return session, err
}

func (s *Store) List() ([]Session, error) {
	entries, err := os.ReadDir(s.dir)
	if err != nil {
		return nil, err
	}

	var sessions []Session
	for _, entry := range entries {
		if entry.IsDir() || filepath.Ext(entry.Name()) != ".json" {
			continue
		}
		id := entry.Name()[:len(entry.Name())-5] // strip .json
		sess, err := s.Load(id)
		if err != nil {
			continue
		}
		sessions = append(sessions, sess)
	}

	sort.Slice(sessions, func(i, j int) bool {
		return sessions[i].ID > sessions[j].ID // newest first
	})
	return sessions, nil
}

func (s *Store) Delete(id string) error {
	path := filepath.Join(s.dir, id+".json")
	return os.Remove(path)
}

func (s *Store) ExportMarkdown(session Session) string {
	md := fmt.Sprintf("# %s — %s\n\n", session.Strategy, session.Timestamp.Format("2006-01-02 15:04:05"))
	md += fmt.Sprintf("**Model:** %s\n\n", session.Model)
	md += fmt.Sprintf("## Query\n\n%s\n\n", session.Query)
	md += fmt.Sprintf("## Response\n\n%s\n\n", session.Response)
	md += "## Metrics\n\n"
	md += "| Metric | Value |\n|---|---|\n"
	md += fmt.Sprintf("| TTFT | %.0fms |\n", session.Metrics.TTFT_MS)
	md += fmt.Sprintf("| Total | %.0fms |\n", session.Metrics.TotalMS)
	md += fmt.Sprintf("| TPS | %.1f |\n", session.Metrics.TPS)
	md += fmt.Sprintf("| Tokens | %d |\n", session.Metrics.TokenCount)
	return md
}
