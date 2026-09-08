package views

import (
	"encoding/json"
	"fmt"
	"strings"

	"agent-reasoning-tui/internal/app"
	"agent-reasoning-tui/internal/client"
	"agent-reasoning-tui/internal/ui"
	"agent-reasoning-tui/internal/viz"

	"github.com/charmbracelet/bubbles/key"
	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"
)

// DebugPhase tracks the lifecycle of a debug session.
type DebugPhase int

const (
	DebugInput     DebugPhase = iota // User types query
	DebugStepping                    // Stepping through events one by one
	DebugRunning                     // Running all remaining events
	DebugComplete                    // Session finished
)

// DebugMsg types for async operations.
type (
	debugStartedMsg struct {
		sessionID string
		err       error
	}
	debugStepResultMsg struct {
		event *client.StructuredEvent
		done  bool
		err   error
	}
	debugRunResultMsg struct {
		events []client.StructuredEvent
		err    error
	}
)

// DebugView is the step-through reasoning debugger.
type DebugView struct {
	ctx *app.Context

	// Input phase
	input *ui.Input

	// Stepping phase
	visualizer  viz.Visualizer
	history     []client.StructuredEvent
	historyIdx  int
	sessionID   string
	phase       DebugPhase
	inspectMode bool // false=visualizer, true=raw JSON
	agentID     string
	prefilledQuery string // set when entering from ChatView with D key

	// Layout
	width  int
	height int

	// Status / error messages
	statusMsg string
}

// DebugKeyMap defines keybindings for DebugView.
type DebugKeyMap struct {
	Next     key.Binding
	Continue key.Binding
	Back     key.Binding
	Inspect  key.Binding
	Quit     key.Binding
	Enter    key.Binding
}

func defaultDebugKeyMap() DebugKeyMap {
	return DebugKeyMap{
		Next: key.NewBinding(
			key.WithKeys("n"),
			key.WithHelp("n", "next step"),
		),
		Continue: key.NewBinding(
			key.WithKeys("c"),
			key.WithHelp("c", "continue all"),
		),
		Back: key.NewBinding(
			key.WithKeys("b"),
			key.WithHelp("b", "back"),
		),
		Inspect: key.NewBinding(
			key.WithKeys("i"),
			key.WithHelp("i", "toggle inspect"),
		),
		Quit: key.NewBinding(
			key.WithKeys("q", "esc"),
			key.WithHelp("q/esc", "quit"),
		),
		Enter: key.NewBinding(
			key.WithKeys("enter"),
			key.WithHelp("enter", "start debug"),
		),
	}
}

// NewDebugView creates a new DebugView.
func NewDebugView(appCtx *app.Context) *DebugView {
	inp := ui.NewInput()
	return &DebugView{
		ctx:   appCtx,
		input: inp,
		phase: DebugInput,
	}
}

// NewDebugViewWithQuery creates a DebugView pre-filled with a query (from ChatView D key).
func NewDebugViewWithQuery(appCtx *app.Context, agentID, query string) *DebugView {
	v := NewDebugView(appCtx)
	v.prefilledQuery = query
	v.agentID = agentID
	return v
}

func (v *DebugView) ID() app.ViewID { return app.ViewDebug }

func (v *DebugView) Init() tea.Cmd {
	v.phase = DebugInput
	v.history = nil
	v.historyIdx = 0
	v.sessionID = ""
	v.statusMsg = ""
	v.inspectMode = false

	// Check ctx.PendingQuery first (set by ChatView D key), then fall back to prefilledQuery.
	if v.ctx.PendingQuery != "" {
		query := v.ctx.PendingQuery
		v.ctx.PendingQuery = ""
		agentID := v.ctx.CurrentAgent
		if agentID == "" {
			agentID = "cot"
		}
		v.agentID = agentID
		v.prefilledQuery = query
		v.input.SetValue(query)
		return v.startDebugSession(agentID, query)
	}

	if v.prefilledQuery != "" {
		// Auto-start with the pre-filled query
		return v.startDebugSession(v.agentID, v.prefilledQuery)
	}
	return nil
}

func (v *DebugView) SetSize(width, height int) {
	v.width = width
	v.height = height
	v.input.SetWidth(width)
}

func (v *DebugView) Update(msg tea.Msg) (app.View, tea.Cmd) {
	keys := defaultDebugKeyMap()

	switch msg := msg.(type) {
	case tea.KeyMsg:
		switch v.phase {
		case DebugInput:
			return v.handleInputPhaseKey(msg, keys)
		case DebugStepping:
			return v.handleSteppingPhaseKey(msg, keys)
		case DebugComplete:
			if key.Matches(msg, keys.Quit) {
				return v, func() tea.Msg { return app.SwitchViewMsg{Target: app.ViewChat} }
			}
		}

	case debugStartedMsg:
		if msg.err != nil {
			v.statusMsg = fmt.Sprintf("Error: %v", msg.err)
			v.phase = DebugInput
			return v, nil
		}
		v.sessionID = msg.sessionID
		v.phase = DebugStepping
		v.statusMsg = "Session started. Press [n] to step, [c] to run all."
		// Fetch the first event
		return v, v.fetchStep()

	case debugStepResultMsg:
		if msg.err != nil {
			v.statusMsg = fmt.Sprintf("Error: %v", msg.err)
			return v, nil
		}
		if msg.done {
			v.phase = DebugComplete
			v.statusMsg = "Complete. Press [q] to return."
			return v, nil
		}
		if msg.event != nil {
			v.history = append(v.history, *msg.event)
			v.historyIdx = len(v.history) - 1
			if v.visualizer != nil {
				v.visualizer.Update(*msg.event)
			}
		}
		return v, nil

	case debugRunResultMsg:
		if msg.err != nil {
			v.statusMsg = fmt.Sprintf("Error: %v", msg.err)
			return v, nil
		}
		for _, evt := range msg.events {
			v.history = append(v.history, evt)
			if v.visualizer != nil {
				v.visualizer.Update(evt)
			}
		}
		v.historyIdx = len(v.history) - 1
		v.phase = DebugComplete
		v.statusMsg = fmt.Sprintf("Complete — %d events total. Press [q] to return.", len(v.history))
	}

	return v, nil
}

func (v *DebugView) handleInputPhaseKey(msg tea.KeyMsg, keys DebugKeyMap) (app.View, tea.Cmd) {
	if key.Matches(msg, keys.Quit) {
		return v, func() tea.Msg { return app.SwitchViewMsg{Target: app.ViewChat} }
	}
	if key.Matches(msg, keys.Enter) {
		query := v.input.Value()
		if query == "" {
			return v, nil
		}
		agentID := v.ctx.CurrentAgent
		if agentID == "" {
			agentID = "cot"
		}
		v.agentID = agentID
		v.statusMsg = "Starting debug session..."
		v.input.Reset()
		return v, v.startDebugSession(agentID, query)
	}
	var cmd tea.Cmd
	v.input, cmd = v.input.Update(msg)
	return v, cmd
}

func (v *DebugView) handleSteppingPhaseKey(msg tea.KeyMsg, keys DebugKeyMap) (app.View, tea.Cmd) {
	switch {
	case key.Matches(msg, keys.Quit):
		if v.sessionID != "" {
			sid := v.sessionID
			v.sessionID = ""
			go v.ctx.ServerClient.DebugCancel(sid) //nolint:errcheck
		}
		return v, func() tea.Msg { return app.SwitchViewMsg{Target: app.ViewChat} }

	case key.Matches(msg, keys.Next):
		if v.sessionID == "" {
			return v, nil
		}
		v.statusMsg = "Fetching next step..."
		return v, v.fetchStep()

	case key.Matches(msg, keys.Continue):
		if v.sessionID == "" {
			return v, nil
		}
		v.statusMsg = "Running all remaining steps..."
		v.phase = DebugRunning
		return v, v.runAll()

	case key.Matches(msg, keys.Back):
		if v.historyIdx > 0 {
			v.historyIdx--
			v.rebuildVisualizer()
		}

	case key.Matches(msg, keys.Inspect):
		v.inspectMode = !v.inspectMode
	}

	return v, nil
}

// startDebugSession initiates a debug session on the server.
func (v *DebugView) startDebugSession(agentID, query string) tea.Cmd {
	model := fmt.Sprintf("%s+%s", v.ctx.CurrentModel, agentID)

	// Set up visualizer for the agent if one exists
	candidate := viz.GetVisualizer(agentID, v.width, v.height)
	if candidate != nil {
		v.visualizer = candidate
		v.visualizer.Reset()
	} else {
		v.visualizer = nil
	}
	v.history = nil
	v.historyIdx = 0
	v.phase = DebugInput // will switch to Stepping on success

	return func() tea.Msg {
		sid, err := v.ctx.ServerClient.DebugStart(model, query, nil)
		return debugStartedMsg{sessionID: sid, err: err}
	}
}

// fetchStep fetches the next event from the debug session.
func (v *DebugView) fetchStep() tea.Cmd {
	sid := v.sessionID
	return func() tea.Msg {
		event, done, err := v.ctx.ServerClient.DebugStep(sid)
		return debugStepResultMsg{event: event, done: done, err: err}
	}
}

// runAll fetches all remaining events at once.
func (v *DebugView) runAll() tea.Cmd {
	sid := v.sessionID
	v.sessionID = "" // session will be deleted server-side
	return func() tea.Msg {
		events, err := v.ctx.ServerClient.DebugRun(sid)
		return debugRunResultMsg{events: events, err: err}
	}
}

// rebuildVisualizer replays events up to historyIdx into a fresh visualizer.
func (v *DebugView) rebuildVisualizer() {
	if v.visualizer == nil {
		return
	}
	v.visualizer.Reset()
	for i := 0; i <= v.historyIdx && i < len(v.history); i++ {
		v.visualizer.Update(v.history[i])
	}
}

func (v *DebugView) View() string {
	switch v.phase {
	case DebugInput:
		return v.renderInputPhase()
	case DebugStepping, DebugRunning, DebugComplete:
		return v.renderDebugPhase()
	}
	return ""
}

func (v *DebugView) renderInputPhase() string {
	titleStyle := lipgloss.NewStyle().
		Bold(true).
		Foreground(lipgloss.Color("86")).
		MarginBottom(1)

	helpStyle := lipgloss.NewStyle().
		Foreground(lipgloss.Color("240"))

	title := titleStyle.Render("Step-Through Debugger")
	subtitle := helpStyle.Render("Select an agent in the sidebar, then type your query and press Enter.")
	inputView := v.input.View()

	var status string
	if v.statusMsg != "" {
		status = lipgloss.NewStyle().Foreground(lipgloss.Color("214")).Render(v.statusMsg)
	}

	parts := []string{title, subtitle, "", inputView}
	if status != "" {
		parts = append(parts, "", status)
	}
	parts = append(parts, "", helpStyle.Render("[esc/q] back to chat"))

	content := lipgloss.JoinVertical(lipgloss.Left, parts...)
	return lipgloss.NewStyle().
		Padding(2, 4).
		Width(v.width).
		Height(v.height).
		Render(content)
}

func (v *DebugView) renderDebugPhase() string {
	// Split into left (visualizer) and right (inspector) panels
	panelW := v.width / 2
	if panelW < 20 {
		panelW = v.width
	}
	inspectorW := v.width - panelW

	controlsHeight := 2
	panelH := v.height - controlsHeight - 1
	if panelH < 1 {
		panelH = 1
	}

	// Left: visualizer or plain text history
	leftContent := v.renderLeftPanel(panelW, panelH)

	// Right: inspector
	rightContent := v.renderRightPanel(inspectorW, panelH)

	// Combine horizontally
	mainRow := lipgloss.JoinHorizontal(lipgloss.Top, leftContent, rightContent)

	// Controls bar
	controls := v.renderControls()

	// Status bar
	statusStyle := lipgloss.NewStyle().
		Foreground(lipgloss.Color("214")).
		Width(v.width)
	status := statusStyle.Render(v.statusMsg)

	return lipgloss.JoinVertical(lipgloss.Left, mainRow, status, controls)
}

func (v *DebugView) renderLeftPanel(w, h int) string {
	panelStyle := lipgloss.NewStyle().
		Border(lipgloss.RoundedBorder()).
		BorderForeground(lipgloss.Color("63")).
		Width(w - 2).
		Height(h - 2)

	var content string
	if v.visualizer != nil && !v.inspectMode {
		content = v.visualizer.View()
	} else {
		// Plain text: show the event at historyIdx
		if len(v.history) == 0 {
			content = lipgloss.NewStyle().Foreground(lipgloss.Color("240")).Render("No events yet.")
		} else {
			idx := v.historyIdx
			if idx < 0 {
				idx = 0
			}
			if idx >= len(v.history) {
				idx = len(v.history) - 1
			}
			evt := v.history[idx]
			headerStyle := lipgloss.NewStyle().Bold(true).Foreground(lipgloss.Color("86"))
			header := headerStyle.Render(fmt.Sprintf("Event %d/%d — %s", idx+1, len(v.history), evt.EventType))

			var sb strings.Builder
			for k, val := range evt.Data {
				sb.WriteString(fmt.Sprintf("%s: %v\n", k, val))
			}
			content = lipgloss.JoinVertical(lipgloss.Left, header, sb.String())
		}
	}

	label := lipgloss.NewStyle().
		Bold(true).
		Foreground(lipgloss.Color("63")).
		Render("Visualizer")

	return panelStyle.Render(lipgloss.JoinVertical(lipgloss.Left, label, content))
}

func (v *DebugView) renderRightPanel(w, h int) string {
	panelStyle := lipgloss.NewStyle().
		Border(lipgloss.RoundedBorder()).
		BorderForeground(lipgloss.Color("214")).
		Width(w - 2).
		Height(h - 2)

	label := lipgloss.NewStyle().
		Bold(true).
		Foreground(lipgloss.Color("214")).
		Render("Inspector")

	var content string
	if len(v.history) == 0 {
		content = lipgloss.NewStyle().Foreground(lipgloss.Color("240")).Render("Waiting for events...")
	} else {
		idx := v.historyIdx
		if idx < 0 {
			idx = 0
		}
		if idx >= len(v.history) {
			idx = len(v.history) - 1
		}
		evt := v.history[idx]

		if v.inspectMode {
			// Raw JSON of the full event
			raw := map[string]interface{}{
				"event_type": evt.EventType,
				"is_update":  evt.IsUpdate,
				"data":       evt.Data,
			}
			b, _ := json.MarshalIndent(raw, "", "  ")
			content = string(b)
		} else {
			// Structured key/value display
			var sb strings.Builder
			keyStyle := lipgloss.NewStyle().Bold(true).Foreground(lipgloss.Color("86"))
			stepInfo := lipgloss.NewStyle().Foreground(lipgloss.Color("240")).
				Render(fmt.Sprintf("Step %d / %d", idx+1, len(v.history)))
			typeStr := keyStyle.Render("type: ") + evt.EventType
			sb.WriteString(stepInfo + "\n")
			sb.WriteString(typeStr + "\n\n")
			for k, val := range evt.Data {
				sb.WriteString(keyStyle.Render(k+": "))
				sb.WriteString(fmt.Sprintf("%v\n", val))
			}
			content = sb.String()
		}
	}

	return panelStyle.Render(lipgloss.JoinVertical(lipgloss.Left, label, content))
}

func (v *DebugView) renderControls() string {
	style := lipgloss.NewStyle().
		Foreground(lipgloss.Color("240")).
		Width(v.width).
		BorderTop(true).
		BorderStyle(lipgloss.NormalBorder()).
		BorderForeground(lipgloss.Color("240"))

	var parts []string
	if v.phase == DebugStepping {
		parts = []string{
			"[n] next step",
			"[c] continue all",
			"[b] back",
			"[i] toggle inspect",
			"[q/esc] quit",
		}
	} else {
		parts = []string{
			"[i] toggle inspect",
			"[b] back",
			"[q/esc] quit",
		}
	}

	return style.Render(strings.Join(parts, "  "))
}
