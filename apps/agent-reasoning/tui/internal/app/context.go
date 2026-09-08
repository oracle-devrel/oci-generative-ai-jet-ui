package app

import (
	"agent-reasoning-tui/internal/client"
	"agent-reasoning-tui/internal/config"
	"agent-reasoning-tui/internal/session"

	tea "github.com/charmbracelet/bubbletea"
)

// ViewID identifies each view in the router.
type ViewID int

const (
	ViewChat ViewID = iota
	ViewArena
	ViewDuel
	ViewDebug
	ViewBenchmark
	ViewSessions
	ViewAgentInfo
)

// View is the interface all TUI views implement.
type View interface {
	Init() tea.Cmd
	Update(msg tea.Msg) (View, tea.Cmd)
	View() string
	SetSize(width, height int)
	ID() ViewID
}

// SwitchViewMsg triggers a view transition.
type SwitchViewMsg struct {
	Target ViewID
}

// AgentInfo holds metadata for one agent (from server /api/agents).
type AgentInfo struct {
	ID            string                     `json:"id"`
	Name          string                     `json:"name"`
	Description   string                     `json:"description"`
	Reference     string                     `json:"reference"`
	BestFor       string                     `json:"best_for"`
	Tradeoffs     string                     `json:"tradeoffs"`
	HasVisualizer bool                       `json:"has_visualizer"`
	Parameters    map[string]ParameterSchema `json:"parameters"`
}

// ParameterSchema describes one tunable hyperparameter.
type ParameterSchema struct {
	Type        string  `json:"type"`
	Default     float64 `json:"default"`
	Min         float64 `json:"min"`
	Max         float64 `json:"max"`
	Description string  `json:"description"`
}

// Context holds shared state injected into all views.
type Context struct {
	ServerClient *client.ServerClient
	OllamaClient *client.OllamaClient
	Config       config.Config
	CurrentModel string
	CurrentAgent string
	Agents       []AgentInfo
	Width        int
	Height       int
	Connected    bool
	ProjectDir   string
	// Active hyperparameter overrides per agent
	AgentParams map[string]map[string]float64
	// Session persistence store
	SessionStore *session.Store
	// PendingQuery is set by SessionsView when re-running a session.
	PendingQuery string
}
