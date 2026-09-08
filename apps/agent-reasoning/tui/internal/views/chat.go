package views

import (
	"context"
	"fmt"
	"os/exec"
	"strings"
	"time"

	"agent-reasoning-tui/internal/app"
	"agent-reasoning-tui/internal/client"
	"agent-reasoning-tui/internal/session"
	"agent-reasoning-tui/internal/ui"
	"agent-reasoning-tui/internal/viz"

	"github.com/charmbracelet/bubbles/key"
	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"
	"github.com/charmbracelet/x/ansi"
)

// Focus represents which component has focus within ChatView.
type Focus int

const (
	FocusSidebar Focus = iota
	FocusInput
)

// Internal message types for streaming.
type (
	streamChunkMsg struct {
		agentID string
		content string
	}
	streamDoneMsg struct {
		agentID  string
		duration float64
	}
	streamErrorMsg struct {
		agentID string
		err     error
	}
	streamStructuredMsg struct {
		agentID string
		event   client.StructuredEvent
	}
	arenaCompleteMsg     struct{}
	benchmarkCompleteMsg struct{ err error }
)

// KeyMap defines the keybindings for ChatView.
type KeyMap struct {
	Up             key.Binding
	Down           key.Binding
	Enter          key.Binding
	Tab            key.Binding
	Escape         key.Binding
	Quit           key.Binding
	ToggleViz      key.Binding
	Debug          key.Binding
	StrategyAdvisor key.Binding
}

func defaultKeyMap() KeyMap {
	return KeyMap{
		Up: key.NewBinding(
			key.WithKeys("up", "k"),
			key.WithHelp("↑/k", "up"),
		),
		Down: key.NewBinding(
			key.WithKeys("down", "j"),
			key.WithHelp("↓/j", "down"),
		),
		Enter: key.NewBinding(
			key.WithKeys("enter"),
			key.WithHelp("enter", "select/submit"),
		),
		Tab: key.NewBinding(
			key.WithKeys("tab"),
			key.WithHelp("tab", "switch focus"),
		),
		Escape: key.NewBinding(
			key.WithKeys("esc"),
			key.WithHelp("esc", "cancel"),
		),
		Quit: key.NewBinding(
			key.WithKeys("ctrl+c", "q"),
			key.WithHelp("q/ctrl+c", "quit"),
		),
		ToggleViz: key.NewBinding(
			key.WithKeys("v"),
			key.WithHelp("v", "toggle viz mode"),
		),
		Debug: key.NewBinding(
			key.WithKeys("d"),
			key.WithHelp("d", "debug last query"),
		),
		StrategyAdvisor: key.NewBinding(
			key.WithKeys("?"),
			key.WithHelp("?", "strategy advisor"),
		),
	}
}

// advisorOverlay holds state for the strategy advisor popup.
type advisorOverlay struct {
	active            bool
	loading           bool
	recommendedID     string
	recommendedName   string
	reason            string
	err               string
}

// advisorResultMsg is sent when the meta-agent response arrives.
type advisorResultMsg struct {
	strategy string // agent ID, e.g. "tot"
	name     string // human name, e.g. "Tree of Thoughts (ToT)"
	reason   string
	err      error
}

// ChatView handles the main chat interface: sidebar, input, streaming, arena, model selector.
type ChatView struct {
	ctx *app.Context

	// UI components
	header        *ui.Header
	sidebar       *ui.Sidebar
	chat          *ui.Chat
	input         *ui.Input
	arena         *ui.Arena
	modelSelector *ui.ModelSelector
	metrics       *ui.MetricsBar
	hyperParams   *ui.HyperParams

	// State
	focus        Focus
	currentAgent string
	width        int
	height       int

	// Streaming control
	streamCancel    context.CancelFunc
	streamRespChan  <-chan client.GenerateResponse
	streamErrChan   <-chan error
	streamEventChan <-chan client.StructuredEvent
	streamStart     time.Time
	streamTTFT      time.Duration
	tokenCount      int
	gotFirstChunk   bool
	lastQuery       string         // saved before input is reset, used for session auto-save
	streamResponse  strings.Builder // accumulates full response for auto-save

	// Visualization
	visualizer viz.Visualizer
	vizMode    bool

	// Strategy advisor overlay
	advisor advisorOverlay

	// Keys
	keys KeyMap
}

// NewChatView creates a ChatView wired to the shared Context.
func NewChatView(appCtx *app.Context) *ChatView {
	header := ui.NewHeader()
	header.SetModel(appCtx.CurrentModel)
	header.SetConnected(appCtx.Connected)

	// Build sidebar from server-fetched agents when available, else use defaults.
	var sidebar *ui.Sidebar
	if len(appCtx.Agents) > 0 {
		items := make([]ui.AgentItem, len(appCtx.Agents))
		for i, a := range appCtx.Agents {
			items[i] = ui.AgentItem{ID: a.ID, Name: a.Name}
		}
		sidebar = ui.NewSidebarFromAgents(items)
	} else {
		sidebar = ui.NewSidebar()
	}

	return &ChatView{
		ctx:           appCtx,
		header:        header,
		sidebar:       sidebar,
		chat:          ui.NewChat(),
		input:         ui.NewInput(),
		arena:         ui.NewArena(),
		modelSelector: ui.NewModelSelector(),
		metrics:       ui.NewMetricsBar(),
		hyperParams:   ui.NewHyperParams(),
		focus:         FocusSidebar,
		currentAgent:  appCtx.CurrentAgent,
		keys:          defaultKeyMap(),
	}
}

// --- app.View interface ---

func (v *ChatView) ID() app.ViewID { return app.ViewChat }

func (v *ChatView) Init() tea.Cmd {
	return nil
}

func (v *ChatView) SetSize(width, height int) {
	v.width = width
	v.height = height
	v.updateSizes()
}

func (v *ChatView) Update(msg tea.Msg) (app.View, tea.Cmd) {
	var cmds []tea.Cmd

	switch msg := msg.(type) {
	case tea.KeyMsg:
		// Hyperparams overlay intercepts all keys when active.
		if v.hyperParams.Active() {
			applied, values := v.hyperParams.Update(msg)
			if applied && len(values) > 0 {
				if v.ctx.AgentParams == nil {
					v.ctx.AgentParams = make(map[string]map[string]float64)
				}
				v.ctx.AgentParams[v.currentAgent] = values
			}
			return v, nil
		}

		// When focused on input but not streaming, j/k and mouse-wheel scroll
		// the chat viewport. Key handling still runs first so Enter submits.
		if v.focus == FocusInput && !v.chat.IsStreaming() && !v.modelSelector.IsActive() && !v.arena.IsActive() {
			_, scrollCmd := v.chat.Update(msg)
			if scrollCmd != nil {
				cmds = append(cmds, scrollCmd)
			}
		}
		view, cmd := v.handleKeyMsg(msg)
		if cmd != nil {
			cmds = append(cmds, cmd)
		}
		return view, tea.Batch(cmds...)

	case tea.MouseMsg:
		// Always forward mouse events to the chat viewport so scroll wheel works.
		if !v.arena.IsActive() && !v.modelSelector.IsActive() {
			_, scrollCmd := v.chat.Update(msg)
			if scrollCmd != nil {
				cmds = append(cmds, scrollCmd)
			}
		}

	case streamChunkMsg:
		if v.arena.IsActive() {
			v.arena.AppendCellContent(msg.agentID, msg.content)
		} else {
			v.streamResponse.WriteString(msg.content)
			v.chat.AppendStreaming(msg.content)
			// Update live metrics on every chunk.
			if !v.gotFirstChunk {
				v.gotFirstChunk = true
				v.streamTTFT = time.Since(v.streamStart)
				v.metrics.SetTTFT(v.streamTTFT)
			}
			v.tokenCount++
			v.metrics.SetTokens(v.tokenCount)
			elapsed := time.Since(v.streamStart)
			if elapsed > 0 {
				v.metrics.SetTPS(float64(v.tokenCount) / elapsed.Seconds())
			}
			v.metrics.SetDuration(elapsed)
		}
		cmds = append(cmds, v.nextStreamChunk(msg.agentID))

	case streamStructuredMsg:
		if v.visualizer != nil {
			v.visualizer.Update(msg.event)
		}
		// Pipe text content into the chat panel so it's always visible.
		// For structured events (chain_step, etc.), extract the content field too.
		var textContent string
		switch msg.event.EventType {
		case "text":
			if c, ok := msg.event.Data["content"].(string); ok {
				textContent = c
			}
		case "chain_step", "thought", "observation", "action", "candidate", "reflection", "critique", "sub_answer":
			if c, ok := msg.event.Data["content"].(string); ok {
				textContent = c
			}
		case "error":
			if m, ok := msg.event.Data["message"].(string); ok {
				textContent = "Error: " + m
			}
		}
		if textContent != "" {
			v.chat.AppendStreaming(textContent)
			if !v.gotFirstChunk {
				v.gotFirstChunk = true
				v.streamTTFT = time.Since(v.streamStart)
				v.metrics.SetTTFT(v.streamTTFT)
			}
			v.tokenCount++
			v.metrics.SetTokens(v.tokenCount)
			elapsed := time.Since(v.streamStart)
			if elapsed > 0 {
				v.metrics.SetTPS(float64(v.tokenCount) / elapsed.Seconds())
			}
			v.metrics.SetDuration(elapsed)
		}
		cmds = append(cmds, v.nextStructuredEvent(msg.agentID))

	case streamDoneMsg:
		if v.arena.IsActive() {
			v.arena.SetCellStatus(msg.agentID, ui.ArenaDone)
			v.arena.SetCellDuration(msg.agentID, msg.duration)
		} else {
			v.chat.FinishStreaming()
			if v.ctx.Config.Sessions.AutoSave && v.ctx.SessionStore != nil {
				fullResponse := v.streamResponse.String()
				totalMS := msg.duration * 1000
				tps := 0.0
				if msg.duration > 0 {
					tps = float64(v.tokenCount) / msg.duration
				}
				s := session.Session{
					ID:       session.GenerateID(v.currentAgent),
					Type:     session.TypeChat,
					Model:    v.ctx.CurrentModel,
					Strategy: v.currentAgent,
					Query:    v.lastQuery,
					Response: fullResponse,
					Metrics: session.Metrics{
						TTFT_MS:    float64(v.streamTTFT.Milliseconds()),
						TotalMS:    totalMS,
						TPS:        tps,
						TokenCount: v.tokenCount,
					},
				}
				go v.ctx.SessionStore.Save(s) //nolint:errcheck
			}
		}

	case streamErrorMsg:
		if v.arena.IsActive() {
			v.arena.SetCellError(msg.agentID, msg.err.Error())
		} else {
			v.chat.AppendStreaming(fmt.Sprintf("\n\n[Error: %v]", msg.err))
			v.chat.FinishStreaming()
		}

	case app.ServerConnectedMsg:
		v.header.SetConnected(true)

	case app.ServerDisconnectedMsg:
		v.header.SetConnected(false)

	case app.AgentsLoadedMsg:
		// Rebuild sidebar with live agents from server.
		items := make([]ui.AgentItem, len(msg.Agents))
		for i, a := range msg.Agents {
			items[i] = ui.AgentItem{ID: a.ID, Name: a.Name}
		}
		v.sidebar = ui.NewSidebarFromAgents(items)
		v.sidebar.SetHeight(v.height - 3 - 3 - 1) // match updateSizes logic

	case modelsLoadedMsg:
		v.modelSelector.SetModels(msg.models)

	case modelsErrorMsg:
		v.modelSelector.SetError(msg.err.Error())

	case arenaCompleteMsg:
		// Arena run finished; nothing extra needed.

	case benchmarkCompleteMsg:
		// Returned from benchmark CLI.

	case advisorResultMsg:
		v.advisor.loading = false
		if msg.err != nil {
			v.advisor.err = msg.err.Error()
		} else {
			v.advisor.recommendedID = msg.strategy
			v.advisor.recommendedName = msg.name
			v.advisor.reason = msg.reason
		}
	}

	return v, tea.Batch(cmds...)
}

func (v *ChatView) View() string {
	// Arena mode view
	if v.arena.IsActive() {
		return lipgloss.JoinVertical(lipgloss.Left,
			v.header.View(),
			v.arena.View(),
		)
	}

	// Normal view
	header := v.header.View()
	sidebar := v.sidebar.View()

	// Use visualizer output when vizMode is active and visualizer is available
	var chatContent string
	if v.vizMode && v.visualizer != nil {
		chatContent = v.visualizer.View()
	} else {
		chatContent = v.chat.View()
	}

	metricsView := v.metrics.View()
	input := v.input.View()

	mainContent := lipgloss.JoinHorizontal(lipgloss.Top, sidebar, chatContent)
	var view string
	if metricsView != "" {
		view = lipgloss.JoinVertical(lipgloss.Left, header, mainContent, metricsView, input)
	} else {
		view = lipgloss.JoinVertical(lipgloss.Left, header, mainContent, input)
	}

	// Overlay model selector if active
	if v.modelSelector.IsActive() {
		selectorView := v.modelSelector.View()
		x := (v.width - 50) / 2
		y := (v.height - 20) / 2
		view = placeOverlay(x, y, selectorView, view)
	}

	// Overlay hyperparameter tuner if active
	if v.hyperParams.Active() {
		hpView := v.hyperParams.View()
		hpW := lipgloss.Width(hpView)
		hpH := lipgloss.Height(hpView)
		x := (v.width - hpW) / 2
		y := (v.height - hpH) / 2
		if x < 0 {
			x = 0
		}
		if y < 0 {
			y = 0
		}
		view = placeOverlay(x, y, hpView, view)
	}

	// Overlay strategy advisor if active
	if v.advisor.active {
		advView := v.renderAdvisorOverlay()
		advW := lipgloss.Width(advView)
		advH := lipgloss.Height(advView)
		x := (v.width - advW) / 2
		y := (v.height - advH) / 2
		if x < 0 {
			x = 0
		}
		if y < 0 {
			y = 0
		}
		view = placeOverlay(x, y, advView, view)
	}

	return view
}

// SyncFromContext pulls shared state that may have been changed externally
// (e.g., connection status updated by the root model).
func (v *ChatView) SyncFromContext() {
	v.header.SetConnected(v.ctx.Connected)
	if v.ctx.CurrentModel != "" {
		v.header.SetModel(v.ctx.CurrentModel)
	}
	// Update input placeholder to reflect connection state.
	if !v.ctx.Connected {
		v.input.SetPlaceholder("Server unavailable — retrying...")
	} else {
		v.input.SetPlaceholder("Enter your query...")
	}
	// Pre-fill query if re-running a session.
	if v.ctx.PendingQuery != "" {
		v.input.SetValue(v.ctx.PendingQuery)
		v.ctx.PendingQuery = ""
		v.focus = FocusInput
		v.input.Focus()
		v.sidebar.SetFocused(false)
	}
}

// --- Key handling ---

func (v *ChatView) handleKeyMsg(msg tea.KeyMsg) (app.View, tea.Cmd) {
	// Strategy advisor overlay intercepts all keys when active
	if v.advisor.active && !v.advisor.loading {
		return v.handleAdvisorKey(msg)
	}

	// Model selector overlay intercepts everything when active
	if v.modelSelector.IsActive() {
		return v.handleModelSelectorKey(msg)
	}

	// Arena mode intercepts everything when active
	if v.arena.IsActive() {
		return v.handleArenaKey(msg)
	}

	// Global keys
	switch {
	case key.Matches(msg, v.keys.Quit):
		if !v.chat.IsStreaming() {
			return v, tea.Quit
		}
		// Cancel streaming on first quit attempt
		if v.streamCancel != nil {
			v.streamCancel()
		}
		v.chat.CancelStreaming()
		return v, nil

	case key.Matches(msg, v.keys.Escape):
		if v.chat.IsStreaming() {
			if v.streamCancel != nil {
				v.streamCancel()
			}
			v.chat.CancelStreaming()
		}
		return v, nil

	case key.Matches(msg, v.keys.Tab):
		v.toggleFocus()
		return v, nil

	case key.Matches(msg, v.keys.ToggleViz):
		v.vizMode = !v.vizMode
		return v, nil

	case msg.String() == "p":
		// Open hyperparameter tuner for the current agent if it has parameters.
		if v.currentAgent != "" {
			for _, a := range v.ctx.Agents {
				if a.ID == v.currentAgent && len(a.Parameters) > 0 {
					v.hyperParams.SetSize(v.width, v.height)
					v.hyperParams.Open(a.Name, a.Parameters)
					break
				}
			}
		}
		return v, nil

	case key.Matches(msg, v.keys.Debug):
		// Switch to debugger, pre-filling current agent and last query if available.
		v.ctx.CurrentAgent = v.currentAgent
		if v.lastQuery != "" {
			v.ctx.PendingQuery = v.lastQuery
		}
		return v, func() tea.Msg { return app.SwitchViewMsg{Target: app.ViewDebug} }
	}

	// Route to focused component
	if v.focus == FocusSidebar {
		return v.handleSidebarKey(msg)
	}
	return v.handleInputKey(msg)
}

func (v *ChatView) handleSidebarKey(msg tea.KeyMsg) (app.View, tea.Cmd) {
	switch {
	case key.Matches(msg, v.keys.Up):
		v.sidebar.MoveUp()
	case key.Matches(msg, v.keys.Down):
		v.sidebar.MoveDown()
	case key.Matches(msg, v.keys.Enter):
		return v.handleSidebarSelect()
	}
	return v, nil
}

func (v *ChatView) handleSidebarSelect() (app.View, tea.Cmd) {
	selected := v.sidebar.Selected()

	switch selected {
	case "arena":
		return v, func() tea.Msg { return app.SwitchViewMsg{Target: app.ViewArena} }

	case "duel":
		return v, func() tea.Msg { return app.SwitchViewMsg{Target: app.ViewDuel} }

	case "benchmark":
		return v, func() tea.Msg { return app.SwitchViewMsg{Target: app.ViewBenchmark} }

	case "debug":
		return v, func() tea.Msg { return app.SwitchViewMsg{Target: app.ViewDebug} }

	case "agentinfo", "agent_info":
		return v, func() tea.Msg { return app.SwitchViewMsg{Target: app.ViewAgentInfo} }

	case "sessions":
		return v, func() tea.Msg { return app.SwitchViewMsg{Target: app.ViewSessions} }

	case "model":
		v.modelSelector.Show()
		v.modelSelector.SetLoading(true)
		return v, v.loadModels()

	default:
		// Select an agent
		v.currentAgent = selected
		item := v.sidebar.SelectedItem()
		v.chat.SetAgent(selected, item.Label)
		v.chat.Clear()
		// Focus input
		v.focus = FocusInput
		v.input.Focus()
		v.sidebar.SetFocused(false)
	}

	return v, nil
}

func (v *ChatView) handleInputKey(msg tea.KeyMsg) (app.View, tea.Cmd) {
	switch {
	case key.Matches(msg, v.keys.StrategyAdvisor):
		query := v.input.Value()
		if query != "" && v.ctx.Connected {
			v.advisor.active = true
			v.advisor.loading = true
			v.advisor.recommendedID = ""
			v.advisor.recommendedName = ""
			v.advisor.reason = ""
			v.advisor.err = ""
			return v, v.queryStrategyAdvisor(query)
		}
		return v, nil

	case key.Matches(msg, v.keys.Enter):
		// Block submission when disconnected.
		if !v.ctx.Connected {
			return v, nil
		}

		query := v.input.Value()
		if query == "" {
			return v, nil
		}

		if v.currentAgent == "arena" {
			v.arena.Start(query)
			v.input.Reset()
			return v, v.startArenaRun(query)
		}

		// Normal chat mode
		v.lastQuery = query
		v.chat.AddUserMessage(query)
		v.chat.StartStreaming()
		v.input.Reset()

		return v, v.startStream(v.currentAgent, query)

	default:
		var cmd tea.Cmd
		v.input, cmd = v.input.Update(msg)
		return v, cmd
	}
}

func (v *ChatView) handleModelSelectorKey(msg tea.KeyMsg) (app.View, tea.Cmd) {
	switch {
	case key.Matches(msg, v.keys.Up):
		v.modelSelector.MoveUp()
	case key.Matches(msg, v.keys.Down):
		v.modelSelector.MoveDown()
	case key.Matches(msg, v.keys.Enter):
		selected := v.modelSelector.Selected()
		if selected != "" {
			v.ctx.CurrentModel = selected
			v.header.SetModel(selected)
		}
		v.modelSelector.Hide()
	case key.Matches(msg, v.keys.Escape):
		v.modelSelector.Hide()
	}
	return v, nil
}

func (v *ChatView) handleArenaKey(msg tea.KeyMsg) (app.View, tea.Cmd) {
	switch {
	case key.Matches(msg, v.keys.Escape):
		v.arena.Stop()
		if v.streamCancel != nil {
			v.streamCancel()
		}
	case key.Matches(msg, v.keys.Quit):
		v.arena.Stop()
		if v.streamCancel != nil {
			v.streamCancel()
		}
		return v, tea.Quit
	}
	return v, nil
}

// --- Focus ---

func (v *ChatView) toggleFocus() {
	if v.focus == FocusSidebar {
		v.focus = FocusInput
		v.sidebar.SetFocused(false)
		v.input.Focus()
	} else {
		v.focus = FocusSidebar
		v.sidebar.SetFocused(true)
		v.input.Blur()
	}
}

// --- Sizing ---

func (v *ChatView) updateSizes() {
	headerHeight := 3
	inputHeight := 3
	metricsHeight := 1
	sidebarWidth := ui.SidebarWidth + 2

	contentHeight := v.height - headerHeight - inputHeight - metricsHeight
	chatWidth := v.width - sidebarWidth

	v.header.SetWidth(v.width)
	v.sidebar.SetHeight(contentHeight)
	v.chat.SetSize(chatWidth, contentHeight)
	v.input.SetWidth(v.width)
	v.metrics.SetWidth(v.width)
	v.arena.SetSize(v.width, v.height-headerHeight)
	v.modelSelector.SetSize(50, 20)
}

// --- Streaming ---

// startStream initiates a new streaming request.
// When viz mode is on and the agent has a visualizer, uses GenerateStructured.
func (v *ChatView) startStream(agentID, query string) tea.Cmd {
	ctx, cancel := context.WithCancel(context.Background())
	v.streamCancel = cancel
	v.streamStart = time.Now()
	v.tokenCount = 0
	v.gotFirstChunk = false
	v.streamTTFT = 0
	v.streamResponse.Reset()
	v.metrics.Reset()
	v.metrics.SetModel(fmt.Sprintf("%s+%s", v.ctx.CurrentModel, agentID))

	// Try structured viz if enabled and agent supports it
	if v.ctx.Config.Defaults.Visualization {
		candidate := viz.GetVisualizer(agentID, v.width, v.height)
		if candidate != nil {
			v.visualizer = candidate
			v.vizMode = true
			v.visualizer.Reset()

			modelWithStrategy := fmt.Sprintf("%s+%s", v.ctx.CurrentModel, agentID)
			v.streamEventChan, v.streamErrChan = v.ctx.ServerClient.GenerateStructured(ctx, modelWithStrategy, query, nil)
			return v.nextStructuredEvent(agentID)
		}
	}

	// Fall back to plain text streaming
	v.visualizer = nil
	v.vizMode = false
	modelWithStrategy := fmt.Sprintf("%s+%s", v.ctx.CurrentModel, agentID)
	if params, ok := v.ctx.AgentParams[agentID]; ok && len(params) > 0 {
		v.streamRespChan, v.streamErrChan = v.ctx.ServerClient.GenerateWithParams(ctx, modelWithStrategy, query, params)
	} else {
		v.streamRespChan, v.streamErrChan = v.ctx.ServerClient.Generate(ctx, modelWithStrategy, query)
	}
	return v.nextStreamChunk(agentID)
}

// nextStreamChunk reads the next chunk from stored channels.
func (v *ChatView) nextStreamChunk(agentID string) tea.Cmd {
	respChan := v.streamRespChan
	errChan := v.streamErrChan
	startTime := v.streamStart

	return func() tea.Msg {
		if respChan == nil {
			return streamDoneMsg{agentID: agentID, duration: 0}
		}
		for {
			select {
			case resp, ok := <-respChan:
				if !ok {
					return streamDoneMsg{agentID: agentID, duration: time.Since(startTime).Seconds()}
				}
				if resp.Response != "" {
					return streamChunkMsg{agentID: agentID, content: resp.Response}
				}
				if resp.Done {
					return streamDoneMsg{agentID: agentID, duration: time.Since(startTime).Seconds()}
				}
			case err, ok := <-errChan:
				if !ok {
					return streamDoneMsg{agentID: agentID, duration: time.Since(startTime).Seconds()}
				}
				if err != nil {
					return streamErrorMsg{agentID: agentID, err: err}
				}
			}
		}
	}
}

// nextStructuredEvent reads the next event from the structured event channel.
func (v *ChatView) nextStructuredEvent(agentID string) tea.Cmd {
	eventChan := v.streamEventChan
	errChan := v.streamErrChan
	startTime := v.streamStart

	return func() tea.Msg {
		if eventChan == nil {
			return streamDoneMsg{agentID: agentID, duration: 0}
		}
		for {
			select {
			case event, ok := <-eventChan:
				if !ok {
					return streamDoneMsg{agentID: agentID, duration: time.Since(startTime).Seconds()}
				}
				return streamStructuredMsg{agentID: agentID, event: event}
			case err, ok := <-errChan:
				if !ok {
					return streamDoneMsg{agentID: agentID, duration: time.Since(startTime).Seconds()}
				}
				if err != nil {
					return streamErrorMsg{agentID: agentID, err: err}
				}
			}
		}
	}
}

// --- Arena ---

func (v *ChatView) startArenaRun(query string) tea.Cmd {
	agents := ui.DefaultAgents()

	return func() tea.Msg {
		ctx, cancel := context.WithCancel(context.Background())
		v.streamCancel = cancel

		type arenaResult struct {
			agentID  string
			content  string
			duration float64
			err      error
		}
		results := make(chan arenaResult, len(agents))

		for _, agent := range agents {
			go func(agentID string) {
				modelWithStrategy := fmt.Sprintf("%s+%s", v.ctx.CurrentModel, agentID)
				startTime := time.Now()

				v.arena.SetCellStatus(agentID, ui.ArenaRunning)

				content, err := v.ctx.ServerClient.GenerateSync(ctx, modelWithStrategy, query)
				duration := time.Since(startTime).Seconds()

				results <- arenaResult{
					agentID:  agentID,
					content:  content,
					duration: duration,
					err:      err,
				}
			}(agent.ID)
		}

		for i := 0; i < len(agents); i++ {
			result := <-results
			if result.err != nil {
				v.arena.SetCellError(result.agentID, result.err.Error())
			} else {
				v.arena.SetCellContent(result.agentID, result.content)
				v.arena.SetCellStatus(result.agentID, ui.ArenaDone)
				v.arena.SetCellDuration(result.agentID, result.duration)
			}
		}

		return arenaCompleteMsg{}
	}
}

// --- Model loading ---

func (v *ChatView) loadModels() tea.Cmd {
	return func() tea.Msg {
		models, err := v.ctx.OllamaClient.ListModels()
		if err != nil {
			return modelsErrorMsg{err: err}
		}
		return modelsLoadedMsg{models: models}
	}
}

// modelsLoadedMsg / modelsErrorMsg are handled internally within ChatView.Update.
type modelsLoadedMsg struct{ models []string }
type modelsErrorMsg struct{ err error }

// --- Strategy Advisor ---

// strategyNames maps agent IDs to display names.
var strategyNames = map[string]string{
	"standard":    "Standard",
	"cot":         "Chain of Thought (CoT)",
	"tot":         "Tree of Thoughts (ToT)",
	"react":       "ReAct",
	"reflection":  "Self-Reflection",
	"consistency": "Self-Consistency",
	"decomposed":  "Decomposed Prompting",
	"least2most":  "Least-to-Most",
	"recursive":   "Recursive LM",
	"refinement":  "Refinement Loop",
	"complex":     "Complex Refinement",
}

// queryStrategyAdvisor sends the query to the meta agent and returns a cmd.
func (v *ChatView) queryStrategyAdvisor(query string) tea.Cmd {
	model := fmt.Sprintf("%s+meta", v.ctx.CurrentModel)
	serverClient := v.ctx.ServerClient
	return func() tea.Msg {
		ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
		defer cancel()
		resp, err := serverClient.GenerateSync(ctx, model, query)
		if err != nil {
			return advisorResultMsg{err: err}
		}
		// Parse strategy from response: look for known strategy IDs.
		respLower := strings.ToLower(resp)
		found := "cot" // sensible default
		foundName := strategyNames["cot"]
		for id, name := range strategyNames {
			if strings.Contains(respLower, id) || strings.Contains(respLower, strings.ToLower(name)) {
				found = id
				foundName = name
				break
			}
		}
		// Extract a short reason: first sentence of the response.
		reason := resp
		if idx := strings.IndexAny(resp, ".!?\n"); idx > 0 && idx < 200 {
			reason = resp[:idx+1]
		} else if len(resp) > 150 {
			reason = resp[:150] + "..."
		}
		return advisorResultMsg{strategy: found, name: foundName, reason: reason}
	}
}

// handleAdvisorKey handles key events when the advisor overlay is visible.
func (v *ChatView) handleAdvisorKey(msg tea.KeyMsg) (app.View, tea.Cmd) {
	switch {
	case key.Matches(msg, v.keys.Enter):
		if v.advisor.recommendedID != "" {
			v.currentAgent = v.advisor.recommendedID
			name := v.advisor.recommendedName
			v.chat.SetAgent(v.advisor.recommendedID, name)
			v.chat.Clear()
			v.focus = FocusInput
			v.input.Focus()
			v.sidebar.SetFocused(false)
		}
		v.advisor.active = false
	case key.Matches(msg, v.keys.Escape):
		v.advisor.active = false
	}
	return v, nil
}

// renderAdvisorOverlay renders the strategy advisor popup box.
func (v *ChatView) renderAdvisorOverlay() string {
	boxStyle := lipgloss.NewStyle().
		Border(lipgloss.RoundedBorder()).
		BorderForeground(lipgloss.Color("63")).
		Padding(1, 2).
		Width(44)

	titleStyle := lipgloss.NewStyle().
		Bold(true).
		Foreground(lipgloss.Color("63"))

	recStyle := lipgloss.NewStyle().
		Bold(true).
		Foreground(lipgloss.Color("10"))

	dimStyle := lipgloss.NewStyle().
		Foreground(lipgloss.Color("240"))

	var body string
	if v.advisor.loading {
		body = "Consulting meta-agent..."
	} else if v.advisor.err != "" {
		body = lipgloss.NewStyle().Foreground(lipgloss.Color("9")).Render("Error: " + v.advisor.err) +
			"\n\n" + dimStyle.Render("[Esc] Close")
	} else {
		body = recStyle.Render("Recommended: "+v.advisor.recommendedName) +
			"\n" + dimStyle.Render("Reason: "+v.advisor.reason) +
			"\n\n" + dimStyle.Render("[Enter] Use  [Esc] Keep current")
	}

	content := titleStyle.Render("Strategy Advisor") + "\n\n" + body
	return boxStyle.Render(content)
}

// --- Benchmark ---

func (v *ChatView) runBenchmarkCLI() tea.Cmd {
	c := exec.Command("python", "agent_cli.py", "--benchmark")
	return tea.ExecProcess(c, func(err error) tea.Msg {
		return benchmarkCompleteMsg{err: err}
	})
}

// --- Overlay helper ---

// ansiDropLeft returns the visible tail of s after skipping n visible columns,
// preserving ANSI escape sequences. It works by truncating a reversed-width
// view: get the full string width, then truncate from the right to (width-n).
func ansiDropLeft(s string, n int) string {
	total := lipgloss.Width(s)
	if n <= 0 {
		return s
	}
	if n >= total {
		return ""
	}
	// Truncate the full string to `total` keeps everything; we want the
	// right (total-n) columns. Achieve this by stripping the left n columns:
	// first build a prefix of exactly n cols, then remove it from the raw
	// string byte-wise (safe because Truncate preserves escape sequences and
	// we only strip the prefix bytes it produced).
	prefix := ansi.Truncate(s, n, "")
	return s[len(prefix):]
}

func placeOverlay(x, y int, overlay, background string) string {
	bgLines := strings.Split(background, "\n")
	overlayLines := strings.Split(overlay, "\n")

	for i, line := range overlayLines {
		bgY := y + i
		if bgY < 0 || bgY >= len(bgLines) {
			continue
		}
		bgLine := bgLines[bgY]
		bgWidth := lipgloss.Width(bgLine)
		if x < 0 || x >= bgWidth {
			continue
		}

		// ANSI-safe left portion (before the overlay).
		before := ansi.Truncate(bgLine, x, "")

		// ANSI-safe right portion (after the overlay).
		endX := x + lipgloss.Width(line)
		after := ""
		if endX < bgWidth {
			after = ansiDropLeft(bgLine, endX)
		}

		bgLines[bgY] = before + line + after
	}

	return strings.Join(bgLines, "\n")
}
