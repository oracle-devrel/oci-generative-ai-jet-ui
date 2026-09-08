package views

import (
	"context"
	"fmt"
	"strings"
	"time"

	"agent-reasoning-tui/internal/app"
	"agent-reasoning-tui/internal/client"
	"agent-reasoning-tui/internal/ui"

	"github.com/charmbracelet/bubbles/key"
	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"
)

// --- Duel-local message types ---

type duelChunkMsg struct {
	side    int // 0 = left, 1 = right
	content string
}

type duelDoneMsg struct {
	side     int
	duration time.Duration
	tokens   int
}

type duelErrorMsg struct {
	side int
	err  error
}

type duelJudgeChunkMsg struct{ content string }
type duelJudgeDoneMsg struct{}
type duelJudgeErrorMsg struct{ err error }

// --- Phase type ---

type DuelPhase int

const (
	DuelSelection DuelPhase = iota
	DuelInput
	DuelRacing
	DuelResults
)

// --- Side state ---

type duelSide struct {
	agentID   string
	agentName string
	content   strings.Builder
	tokens    int
	tps       float64
	ttft      time.Duration
	duration  time.Duration
	startTime time.Time
	done      bool
	err       string

	respChan <-chan client.GenerateResponse
	errChan  <-chan error
	cancel   context.CancelFunc
}

// --- View ---

type DuelView struct {
	ctx    *app.Context
	phase  DuelPhase
	input  *ui.Input
	query  string
	width  int
	height int
	keys   KeyMap

	// Agent selection
	agents   []ui.Agent
	selected [2]int // indices into agents slice, -1 = not set
	cursor   int    // current cursor in selection list

	// Sides
	left  duelSide
	right duelSide

	// Judge
	judgeContent strings.Builder
	judgeRunning bool
	judgeDone    bool
	judgeCancel  context.CancelFunc
	judgeRespCh  <-chan client.GenerateResponse
	judgeErrCh   <-chan error
}

// getAgents returns the live agent list from ctx if populated, else defaults.
func (v *DuelView) getAgents() []ui.Agent {
	if len(v.ctx.Agents) > 0 {
		agents := make([]ui.Agent, len(v.ctx.Agents))
		for i, a := range v.ctx.Agents {
			agents[i] = ui.Agent{ID: a.ID, Name: a.Name}
		}
		return agents
	}
	return ui.DefaultAgents()
}

func NewDuelView(appCtx *app.Context) *DuelView {
	v := &DuelView{
		ctx:      appCtx,
		phase:    DuelSelection,
		input:    ui.NewInput(),
		selected: [2]int{-1, -1},
		keys:     defaultKeyMap(),
	}
	v.agents = v.getAgents()
	return v
}

func (v *DuelView) ID() app.ViewID { return app.ViewDuel }

func (v *DuelView) Init() tea.Cmd {
	v.phase = DuelSelection
	v.query = ""
	v.selected = [2]int{-1, -1}
	v.cursor = 0
	v.left = duelSide{}
	v.right = duelSide{}
	v.judgeContent.Reset()
	v.judgeRunning = false
	v.judgeDone = false
	v.input.Reset()
	// Refresh agent list in case ctx.Agents was populated after construction.
	v.agents = v.getAgents()
	return nil
}

func (v *DuelView) SetSize(width, height int) {
	v.width = width
	v.height = height
	v.input.SetWidth(width)
}

// --- Update ---

func (v *DuelView) Update(msg tea.Msg) (app.View, tea.Cmd) {
	var cmds []tea.Cmd

	switch msg := msg.(type) {
	case tea.KeyMsg:
		view, cmd := v.handleKey(msg)
		return view, cmd

	case duelChunkMsg:
		side := v.sidePtr(msg.side)
		if side != nil {
			side.content.WriteString(msg.content)
			side.tokens++
			elapsed := time.Since(side.startTime)
			if side.ttft == 0 {
				side.ttft = elapsed
			}
			if elapsed > 0 {
				side.tps = float64(side.tokens) / elapsed.Seconds()
			}
		}
		cmds = append(cmds, v.nextDuelChunk(msg.side))

	case duelDoneMsg:
		side := v.sidePtr(msg.side)
		if side != nil {
			side.done = true
			side.duration = msg.duration
			side.tokens = msg.tokens
			elapsed := time.Since(side.startTime)
			if elapsed > 0 && msg.tokens > 0 {
				side.tps = float64(msg.tokens) / elapsed.Seconds()
			}
		}
		if v.left.done && v.right.done {
			v.phase = DuelResults
		}

	case duelErrorMsg:
		side := v.sidePtr(msg.side)
		if side != nil {
			side.err = msg.err.Error()
			side.done = true
		}
		if v.left.done && v.right.done {
			v.phase = DuelResults
		}

	case duelJudgeChunkMsg:
		v.judgeContent.WriteString(msg.content)
		cmds = append(cmds, v.nextJudgeChunk())

	case duelJudgeDoneMsg:
		v.judgeRunning = false
		v.judgeDone = true

	case duelJudgeErrorMsg:
		v.judgeRunning = false
		v.judgeContent.WriteString(fmt.Sprintf("\n[Judge error: %v]", msg.err))
		v.judgeDone = true

	case app.ServerConnectedMsg, app.ServerDisconnectedMsg:
		// no-op
	}

	return v, tea.Batch(cmds...)
}

func (v *DuelView) handleKey(msg tea.KeyMsg) (app.View, tea.Cmd) {
	switch v.phase {
	case DuelSelection:
		switch {
		case key.Matches(msg, v.keys.Escape):
			return v, func() tea.Msg { return app.SwitchViewMsg{Target: app.ViewChat} }
		case key.Matches(msg, v.keys.Up):
			if v.cursor > 0 {
				v.cursor--
			}
		case key.Matches(msg, v.keys.Down):
			if v.cursor < len(v.agents)-1 {
				v.cursor++
			}
		case key.Matches(msg, v.keys.Enter):
			return v.handleSelectionEnter()
		}

	case DuelInput:
		switch {
		case key.Matches(msg, v.keys.Escape):
			// Go back to selection
			v.phase = DuelSelection
			v.selected = [2]int{-1, -1}
		case key.Matches(msg, v.keys.Enter):
			q := v.input.Value()
			if q == "" {
				return v, nil
			}
			v.query = q
			v.input.Reset()
			v.phase = DuelRacing
			return v, v.startDuel(q)
		default:
			var cmd tea.Cmd
			v.input, cmd = v.input.Update(msg)
			return v, cmd
		}

	case DuelRacing:
		switch {
		case key.Matches(msg, v.keys.Escape), key.Matches(msg, v.keys.Quit):
			v.cancelAll()
			return v, func() tea.Msg { return app.SwitchViewMsg{Target: app.ViewChat} }
		}

	case DuelResults:
		switch {
		case key.Matches(msg, v.keys.Escape):
			return v, func() tea.Msg { return app.SwitchViewMsg{Target: app.ViewChat} }
		case msg.String() == "j":
			if !v.judgeRunning && !v.judgeDone {
				return v, v.startJudge()
			}
		case key.Matches(msg, v.keys.Enter):
			// Re-run same duel
			v.left.content.Reset()
			v.right.content.Reset()
			v.left.done = false
			v.right.done = false
			v.judgeContent.Reset()
			v.judgeRunning = false
			v.judgeDone = false
			v.phase = DuelRacing
			return v, v.startDuel(v.query)
		}
	}

	return v, nil
}

func (v *DuelView) handleSelectionEnter() (app.View, tea.Cmd) {
	// First press selects left agent, second selects right
	if v.selected[0] == -1 {
		v.selected[0] = v.cursor
	} else if v.selected[1] == -1 && v.cursor != v.selected[0] {
		v.selected[1] = v.cursor
		// Both selected, move to input phase
		leftAgent := v.agents[v.selected[0]]
		rightAgent := v.agents[v.selected[1]]
		v.left = duelSide{agentID: leftAgent.ID, agentName: leftAgent.Name}
		v.right = duelSide{agentID: rightAgent.ID, agentName: rightAgent.Name}
		v.phase = DuelInput
		v.input.Focus()
	}
	return v, nil
}

func (v *DuelView) sidePtr(side int) *duelSide {
	if side == 0 {
		return &v.left
	}
	return &v.right
}

// --- Streaming ---

func (v *DuelView) startDuel(query string) tea.Cmd {
	// Left side
	ctxL, cancelL := context.WithCancel(context.Background())
	v.left.cancel = cancelL
	v.left.startTime = time.Now()
	v.left.content.Reset()
	v.left.tokens = 0
	v.left.done = false
	v.left.err = ""
	modelL := fmt.Sprintf("%s+%s", v.ctx.CurrentModel, v.left.agentID)
	v.left.respChan, v.left.errChan = v.ctx.ServerClient.Generate(ctxL, modelL, query)

	// Right side
	ctxR, cancelR := context.WithCancel(context.Background())
	v.right.cancel = cancelR
	v.right.startTime = time.Now()
	v.right.content.Reset()
	v.right.tokens = 0
	v.right.done = false
	v.right.err = ""
	modelR := fmt.Sprintf("%s+%s", v.ctx.CurrentModel, v.right.agentID)
	v.right.respChan, v.right.errChan = v.ctx.ServerClient.Generate(ctxR, modelR, query)

	return tea.Batch(
		v.nextDuelChunkFrom(0, &v.left),
		v.nextDuelChunkFrom(1, &v.right),
	)
}

func (v *DuelView) nextDuelChunk(side int) tea.Cmd {
	s := v.sidePtr(side)
	if s == nil || s.done {
		return nil
	}
	return v.nextDuelChunkFrom(side, s)
}

func (v *DuelView) nextDuelChunkFrom(side int, s *duelSide) tea.Cmd {
	respChan := s.respChan
	errChan := s.errChan
	startTime := s.startTime
	tokens := &s.tokens // pointer so the closure reads the live counter

	return func() tea.Msg {
		for {
			select {
			case resp, ok := <-respChan:
				if !ok {
					elapsed := time.Since(startTime)
					return duelDoneMsg{side: side, duration: elapsed, tokens: *tokens}
				}
				if resp.Response != "" {
					return duelChunkMsg{side: side, content: resp.Response}
				}
				if resp.Done {
					elapsed := time.Since(startTime)
					return duelDoneMsg{side: side, duration: elapsed, tokens: *tokens}
				}
			case err, ok := <-errChan:
				if ok && err != nil {
					return duelErrorMsg{side: side, err: err}
				}
			}
		}
	}
}

func (v *DuelView) cancelAll() {
	if v.left.cancel != nil {
		v.left.cancel()
	}
	if v.right.cancel != nil {
		v.right.cancel()
	}
	if v.judgeCancel != nil {
		v.judgeCancel()
	}
}

// --- LLM Judge ---

func (v *DuelView) startJudge() tea.Cmd {
	v.judgeRunning = true
	v.judgeContent.Reset()

	prompt := fmt.Sprintf(
		"Compare these two responses to: '%s'\n\nResponse A (%s):\n%s\n\nResponse B (%s):\n%s\n\nWhich is better and why? Be brief.",
		v.query,
		v.left.agentName, v.left.content.String(),
		v.right.agentName, v.right.content.String(),
	)

	ctx, cancel := context.WithCancel(context.Background())
	v.judgeCancel = cancel

	// Use standard model (no strategy) for judge
	respCh, errCh := v.ctx.ServerClient.Generate(ctx, v.ctx.CurrentModel, prompt)
	v.judgeRespCh = respCh
	v.judgeErrCh = errCh

	return v.nextJudgeChunk()
}

func (v *DuelView) nextJudgeChunk() tea.Cmd {
	respCh := v.judgeRespCh
	errCh := v.judgeErrCh

	return func() tea.Msg {
		for {
			select {
			case resp, ok := <-respCh:
				if !ok {
					return duelJudgeDoneMsg{}
				}
				if resp.Response != "" {
					return duelJudgeChunkMsg{content: resp.Response}
				}
				if resp.Done {
					return duelJudgeDoneMsg{}
				}
			case err, ok := <-errCh:
				if ok && err != nil {
					return duelJudgeErrorMsg{err: err}
				}
			}
		}
	}
}

// --- View rendering ---

func (v *DuelView) View() string {
	switch v.phase {
	case DuelSelection:
		return v.renderSelection()
	case DuelInput:
		return v.renderInput()
	case DuelRacing:
		return v.renderRacing()
	case DuelResults:
		return v.renderResults()
	}
	return ""
}

func (v *DuelView) headerStyle() lipgloss.Style {
	return lipgloss.NewStyle().
		Bold(true).
		Foreground(ui.ColorPrimary).
		Width(v.width).
		Padding(0, 1)
}

func (v *DuelView) renderSelection() string {
	title := v.headerStyle().Render("Head-to-Head Duel  —  Select two agents")
	hint := lipgloss.NewStyle().Foreground(ui.ColorMuted).Render("  Enter to select  |  Esc → back to chat")

	var sb strings.Builder
	for i, a := range v.agents {
		var prefix string
		marker := ""

		if v.selected[0] == i {
			marker = lipgloss.NewStyle().Foreground(ui.ColorPrimary).Render(" [LEFT]")
		} else if v.selected[1] == i {
			marker = lipgloss.NewStyle().Foreground(ui.ColorSecondary).Render(" [RIGHT]")
		}

		if i == v.cursor {
			prefix = lipgloss.NewStyle().Foreground(ui.ColorPrimary).Bold(true).Render("  > ")
		} else {
			prefix = "    "
		}

		sb.WriteString(fmt.Sprintf("%s%s%s\n", prefix, a.Name, marker))
	}

	return lipgloss.JoinVertical(lipgloss.Left, title, "", sb.String(), hint)
}

func (v *DuelView) renderInput() string {
	leftName := v.left.agentName
	rightName := v.right.agentName

	title := v.headerStyle().Render(fmt.Sprintf("Duel: %s  vs  %s  —  Enter your query", leftName, rightName))
	hint := lipgloss.NewStyle().Foreground(ui.ColorMuted).Render("  Esc → re-select agents")

	return lipgloss.JoinVertical(lipgloss.Left,
		title,
		"",
		"  Query: "+v.input.View(),
		hint,
	)
}

func (v *DuelView) renderRacing() string {
	title := v.headerStyle().Render(fmt.Sprintf("Duel: %s  vs  %s  |  Esc → exit", v.left.agentName, v.right.agentName))

	half := (v.width - 1) / 2
	contentH := v.height - 8
	if contentH < 4 {
		contentH = 4
	}

	leftPanel := v.renderSidePanel(&v.left, half, contentH, ui.ColorPrimary)
	rightPanel := v.renderSidePanel(&v.right, half, contentH, ui.ColorSecondary)

	splitLine := lipgloss.NewStyle().Foreground(ui.ColorMuted).Render("│")
	racePanels := lipgloss.JoinHorizontal(lipgloss.Top, leftPanel, splitLine, rightPanel)

	metrics := v.renderMetricsBar()

	return lipgloss.JoinVertical(lipgloss.Left, title, racePanels, metrics)
}

func (v *DuelView) renderSidePanel(s *duelSide, width, height int, color lipgloss.Color) string {
	content := s.content.String()
	if s.err != "" {
		content = "[Error: " + s.err + "]"
	}

	// Show last N lines
	lines := strings.Split(content, "\n")
	maxLines := height
	if len(lines) > maxLines {
		lines = lines[len(lines)-maxLines:]
	}
	maxLineLen := width - 4
	if maxLineLen < 1 {
		maxLineLen = 1
	}
	for i, line := range lines {
		if len(line) > maxLineLen {
			lines[i] = line[:maxLineLen-1] + "…"
		}
	}

	statusStr := "streaming..."
	if s.done {
		statusStr = fmt.Sprintf("done %.1fs", s.duration.Seconds())
	}

	header := lipgloss.NewStyle().Bold(true).Foreground(color).
		Render(fmt.Sprintf("%s  [%s]", s.agentName, statusStr))

	body := header + "\n" + strings.Join(lines, "\n")

	return lipgloss.NewStyle().
		Width(width).
		Height(height + 2).
		Padding(0, 1).
		Render(body)
}

func (v *DuelView) renderMetricsBar() string {
	leftTTFT := "-"
	leftTok := "-"
	leftTPS := "-"
	rightTTFT := "-"
	rightTok := "-"
	rightTPS := "-"

	if v.left.ttft > 0 {
		leftTTFT = fmt.Sprintf("%.2fs", v.left.ttft.Seconds())
	}
	if v.left.tokens > 0 {
		leftTok = fmt.Sprintf("%d", v.left.tokens)
		leftTPS = fmt.Sprintf("%.1f", v.left.tps)
	}
	if v.right.ttft > 0 {
		rightTTFT = fmt.Sprintf("%.2fs", v.right.ttft.Seconds())
	}
	if v.right.tokens > 0 {
		rightTok = fmt.Sprintf("%d", v.right.tokens)
		rightTPS = fmt.Sprintf("%.1f", v.right.tps)
	}

	leftMetrics := fmt.Sprintf("TTFT: %s  Tokens: %s  TPS: %s", leftTTFT, leftTok, leftTPS)
	rightMetrics := fmt.Sprintf("TTFT: %s  Tokens: %s  TPS: %s", rightTTFT, rightTok, rightTPS)

	half := v.width / 2
	leftStr := lipgloss.NewStyle().Width(half).Foreground(ui.ColorPrimary).Render(leftMetrics)
	rightStr := lipgloss.NewStyle().Width(half).Foreground(ui.ColorSecondary).Render(rightMetrics)

	return lipgloss.JoinHorizontal(lipgloss.Top, leftStr, rightStr)
}

func (v *DuelView) renderResults() string {
	title := v.headerStyle().Render(fmt.Sprintf("Results: %s  vs  %s", v.left.agentName, v.right.agentName))

	half := (v.width - 1) / 2
	resultH := v.height - 16
	if resultH < 4 {
		resultH = 4
	}

	leftPanel := v.renderSidePanel(&v.left, half, resultH, ui.ColorPrimary)
	rightPanel := v.renderSidePanel(&v.right, half, resultH, ui.ColorSecondary)
	splitLine := lipgloss.NewStyle().Foreground(ui.ColorMuted).Render("│")
	panels := lipgloss.JoinHorizontal(lipgloss.Top, leftPanel, splitLine, rightPanel)

	metrics := v.renderMetricsBar()

	var judgeSection string
	if !v.judgeRunning && !v.judgeDone {
		judgeSection = lipgloss.NewStyle().Foreground(ui.ColorMuted).
			Render("  Press j for LLM judge verdict  |  Enter to re-run  |  Esc to exit")
	} else if v.judgeRunning {
		judgeSection = lipgloss.NewStyle().Foreground(ui.ColorWarning).
			Render("  Judge is thinking...")
	} else {
		judgeStyle := lipgloss.NewStyle().
			Border(lipgloss.RoundedBorder()).
			BorderForeground(ui.ColorWarning).
			Padding(0, 1).
			Width(v.width - 4)
		judgeSection = judgeStyle.Render("Judge verdict:\n" + v.judgeContent.String())
	}

	return lipgloss.JoinVertical(lipgloss.Left, title, panels, metrics, "", judgeSection)
}
