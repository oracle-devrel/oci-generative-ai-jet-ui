package app

import (
	"os"
	"path/filepath"
	"time"

	"agent-reasoning-tui/internal/client"
	"agent-reasoning-tui/internal/config"
	"agent-reasoning-tui/internal/session"

	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"
)

// AgentsLoadedMsg is sent when /api/agents is fetched successfully.
type AgentsLoadedMsg struct{ Agents []AgentInfo }

// agentsErrorMsg is sent when the /api/agents fetch fails (internal only).
type agentsErrorMsg struct{ err error }

// Messages for async operations handled at the root level.
// Exported so views can react to connection state changes.
type (
	ServerConnectedMsg    struct{}
	ServerDisconnectedMsg struct{}
)

// retryTickMsg is sent when the health-check retry timer fires.
type retryTickMsg struct{}

// Model is the root Bubble Tea model. It owns the Router and shared Context,
// handles global concerns (window resize, connection health, quit), and
// delegates everything else to the active View via the Router.
type Model struct {
	ctx    *Context
	router *Router

	quitting    bool
	retryDelay  time.Duration // current backoff delay
}

// New creates a new application model with default config (backward-compatible).
func New() *Model {
	return NewWithConfig(config.DefaultConfig(), "")
}

// NewWithConfig creates a new application model with explicit config and project dir.
func NewWithConfig(cfg config.Config, projectDir string) *Model {
	// Build session store dir relative to project directory.
	sessDir := filepath.Join(projectDir, "data", "sessions")
	if projectDir == "" {
		home, _ := os.UserHomeDir()
		sessDir = filepath.Join(home, ".agent-reasoning", "sessions")
	}

	appCtx := &Context{
		ServerClient: client.NewServerClient(),
		OllamaClient: client.NewOllamaClient(),
		Config:       cfg,
		CurrentModel: cfg.Defaults.Model,
		CurrentAgent: "standard",
		Connected:    false,
		ProjectDir:   projectDir,
		AgentParams:  make(map[string]map[string]float64),
		SessionStore: session.NewStore(sessDir),
	}

	// The Router starts with no views. Views are registered by the caller
	// (main.go) after they are created with access to the Context.
	router := NewRouter(map[ViewID]View{}, ViewChat)

	return &Model{
		ctx:    appCtx,
		router: router,
	}
}

// Context returns the shared context so callers (main.go) can create views.
func (m *Model) Ctx() *Context {
	return m.ctx
}

// Router returns the router so callers can register views.
func (m *Model) Router() *Router {
	return m.router
}

// Init starts connection health check and enters alt screen.
func (m *Model) Init() tea.Cmd {
	initCmd := m.router.SwitchTo(ViewChat)
	return tea.Batch(
		m.checkConnection(),
		tea.EnterAltScreen,
		initCmd,
	)
}

// checkConnection checks if the server is healthy.
func (m *Model) checkConnection() tea.Cmd {
	return func() tea.Msg {
		if m.ctx.ServerClient.IsHealthy() {
			return ServerConnectedMsg{}
		}
		return ServerDisconnectedMsg{}
	}
}

// retryHealthCheck returns a cmd that fires retryTickMsg after retryDelay.
func (m *Model) retryHealthCheck() tea.Cmd {
	delay := m.retryDelay
	return tea.Tick(delay, func(time.Time) tea.Msg {
		return retryTickMsg{}
	})
}

// Update handles messages. Global concerns are handled here; everything else
// is forwarded to the router (which forwards to the active View).
func (m *Model) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	switch msg := msg.(type) {
	case tea.WindowSizeMsg:
		m.ctx.Width = msg.Width
		m.ctx.Height = msg.Height
		m.router.SetSize(msg.Width, msg.Height)
		return m, nil

	case ServerConnectedMsg:
		m.ctx.Connected = true
		// Notify the active view so it can update its header, and kick off agent load.
		cmd := m.router.Update(msg)
		return m, tea.Batch(cmd, m.loadAgents())

	case AgentsLoadedMsg:
		m.ctx.Agents = msg.Agents
		// Forward so views (e.g. ChatView) can rebuild their sidebars.
		cmd := m.router.Update(msg)
		return m, cmd

	case agentsErrorMsg:
		// Non-fatal: fall back to defaults; just drop the message.
		return m, nil

	case ServerDisconnectedMsg:
		m.ctx.Connected = false
		if m.retryDelay == 0 {
			m.retryDelay = 3 * time.Second
		}
		cmd := m.router.Update(msg)
		retryCmd := m.retryHealthCheck()
		return m, tea.Batch(cmd, retryCmd)

	case retryTickMsg:
		if m.ctx.ServerClient.IsHealthy() {
			m.ctx.Connected = true
			m.retryDelay = 0
			cmd := m.router.Update(ServerConnectedMsg{})
			return m, cmd
		}
		// Increase backoff up to 30 seconds.
		m.retryDelay *= 2
		if m.retryDelay > 30*time.Second {
			m.retryDelay = 30 * time.Second
		}
		return m, m.retryHealthCheck()

	case SwitchViewMsg:
		cmd := m.router.SwitchTo(msg.Target)
		return m, cmd
	}

	// Everything else goes to the active view via the router.
	cmd := m.router.Update(msg)
	return m, cmd
}

// loadAgents fetches /api/agents and converts the result into app.AgentInfo slice.
func (m *Model) loadAgents() tea.Cmd {
	return func() tea.Msg {
		agents, err := m.ctx.ServerClient.ListAgents()
		if err != nil {
			return agentsErrorMsg{err: err}
		}
		var infos []AgentInfo
		for _, a := range agents {
			params := make(map[string]ParameterSchema)
			for k, v := range a.Parameters {
				params[k] = ParameterSchema{
					Type:        v.Type,
					Default:     v.Default,
					Min:         v.Min,
					Max:         v.Max,
					Description: v.Description,
				}
			}
			infos = append(infos, AgentInfo{
				ID:            a.ID,
				Name:          a.Name,
				Description:   a.Description,
				Reference:     a.Reference,
				BestFor:       a.BestFor,
				Tradeoffs:     a.Tradeoffs,
				HasVisualizer: a.HasVisualizer,
				Parameters:    params,
			})
		}
		return AgentsLoadedMsg{Agents: infos}
	}
}

// View renders the application. If quitting, show goodbye; otherwise delegate.
func (m *Model) View() string {
	if m.quitting {
		return "Goodbye!\n"
	}
	if m.ctx.Width > 0 && m.ctx.Height > 0 && (m.ctx.Width < 80 || m.ctx.Height < 24) {
		return lipgloss.Place(m.ctx.Width, m.ctx.Height, lipgloss.Center, lipgloss.Center,
			"Terminal too small (need 80×24)")
	}
	return m.router.View()
}
