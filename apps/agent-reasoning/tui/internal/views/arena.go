package views

import (
	"context"
	"fmt"
	"sort"
	"strings"
	"time"

	"agent-reasoning-tui/internal/app"
	"agent-reasoning-tui/internal/client"
	"agent-reasoning-tui/internal/ui"

	"github.com/charmbracelet/bubbles/key"
	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"
)

// --- Arena-local message types ---

type arenaCellChunkMsg struct {
	agentID string
	content string
}

type arenaCellDoneMsg struct {
	agentID   string
	duration  time.Duration
	tokens    int
}

type arenaCellErrorMsg struct {
	agentID string
	err     error
}

// --- Status and phase types ---

type ArenaCellStatus int

const (
	CellWaiting ArenaCellStatus = iota
	CellRunning
	CellDone
	CellError
)

type ArenaPhase int

const (
	ArenaInput ArenaPhase = iota
	ArenaRacing
	ArenaSummary
)

// --- Cell type ---

type ArenaCell struct {
	AgentID   string
	AgentName string
	Status    ArenaCellStatus
	Content   strings.Builder
	Tokens    int
	TPS       float64
	Duration  time.Duration
	StartTime time.Time
	Error     string
}

// --- View ---

type ArenaView struct {
	ctx        *app.Context
	cells      []*ArenaCell
	cellStates map[string]*perCellState
	query      string
	input      *ui.Input
	phase      ArenaPhase
	cancels    []context.CancelFunc
	finished   []string // agent IDs in finish order
	width      int
	height     int
	keys       KeyMap
}

func NewArenaView(appCtx *app.Context) *ArenaView {
	return &ArenaView{
		ctx:        appCtx,
		input:      ui.NewInput(),
		phase:      ArenaInput,
		keys:       defaultKeyMap(),
		cellStates: make(map[string]*perCellState),
	}
}

func (v *ArenaView) ID() app.ViewID { return app.ViewArena }

func (v *ArenaView) Init() tea.Cmd {
	v.phase = ArenaInput
	v.query = ""
	v.finished = nil
	v.cancels = nil
	v.input.Reset()
	v.input.Focus()
	v.rebuildCells()
	return nil
}

func (v *ArenaView) SetSize(width, height int) {
	v.width = width
	v.height = height
	v.input.SetWidth(width)
}

// getAgents returns the live agent list from ctx if populated, else defaults.
func (v *ArenaView) getAgents() []ui.Agent {
	if len(v.ctx.Agents) > 0 {
		agents := make([]ui.Agent, len(v.ctx.Agents))
		for i, a := range v.ctx.Agents {
			agents[i] = ui.Agent{ID: a.ID, Name: a.Name}
		}
		return agents
	}
	return ui.DefaultAgents()
}

func (v *ArenaView) rebuildCells() {
	agents := v.getAgents()
	v.cells = make([]*ArenaCell, len(agents))
	for i, a := range agents {
		v.cells[i] = &ArenaCell{
			AgentID:   a.ID,
			AgentName: a.Name,
			Status:    CellWaiting,
		}
	}
}

// --- Update ---

func (v *ArenaView) Update(msg tea.Msg) (app.View, tea.Cmd) {
	var cmds []tea.Cmd

	switch msg := msg.(type) {
	case tea.KeyMsg:
		view, cmd := v.handleKey(msg)
		return view, cmd

	case arenaCellChunkMsg:
		cell := v.findCell(msg.agentID)
		if cell != nil {
			cell.Content.WriteString(msg.content)
			cell.Tokens++
			elapsed := time.Since(cell.StartTime)
			if elapsed > 0 {
				cell.TPS = float64(cell.Tokens) / elapsed.Seconds()
			}
		}
		cmds = append(cmds, v.nextChunk(msg.agentID))

	case arenaCellDoneMsg:
		cell := v.findCell(msg.agentID)
		if cell != nil {
			cell.Status = CellDone
			cell.Duration = msg.duration
			cell.Tokens = msg.tokens
			elapsed := time.Since(cell.StartTime)
			if elapsed > 0 && msg.tokens > 0 {
				cell.TPS = float64(msg.tokens) / elapsed.Seconds()
			}
		}
		v.finished = append(v.finished, msg.agentID)
		if v.allDone() {
			v.phase = ArenaSummary
		}

	case arenaCellErrorMsg:
		cell := v.findCell(msg.agentID)
		if cell != nil {
			cell.Status = CellError
			cell.Error = msg.err.Error()
		}
		v.finished = append(v.finished, msg.agentID)
		if v.allDone() {
			v.phase = ArenaSummary
		}

	case app.ServerConnectedMsg, app.ServerDisconnectedMsg:
		// no-op for arena
	}

	return v, tea.Batch(cmds...)
}

func (v *ArenaView) handleKey(msg tea.KeyMsg) (app.View, tea.Cmd) {
	switch v.phase {
	case ArenaInput:
		switch {
		case key.Matches(msg, v.keys.Escape):
			return v, tea.Cmd(func() tea.Msg { return app.SwitchViewMsg{Target: app.ViewChat} })
		case key.Matches(msg, v.keys.Enter):
			q := v.input.Value()
			if q == "" {
				return v, nil
			}
			v.query = q
			v.input.Reset()
			v.phase = ArenaRacing
			return v, v.startRace(q)
		default:
			var cmd tea.Cmd
			v.input, cmd = v.input.Update(msg)
			return v, cmd
		}

	case ArenaRacing:
		switch {
		case key.Matches(msg, v.keys.Escape), key.Matches(msg, v.keys.Quit):
			v.cancelAll()
			return v, tea.Cmd(func() tea.Msg { return app.SwitchViewMsg{Target: app.ViewChat} })
		}

	case ArenaSummary:
		switch {
		case key.Matches(msg, v.keys.Escape):
			return v, tea.Cmd(func() tea.Msg { return app.SwitchViewMsg{Target: app.ViewChat} })
		case key.Matches(msg, v.keys.Enter):
			// Re-run with same query
			v.rebuildCells()
			v.finished = nil
			v.phase = ArenaRacing
			return v, v.startRace(v.query)
		}
	}

	return v, nil
}

// --- Racing logic ---

// perCellState holds per-cell channels so nextChunk can close over them.
type perCellState struct {
	respChan  <-chan client.GenerateResponse
	errChan   <-chan error
	startTime time.Time
	tokens    int
}

func (v *ArenaView) startRace(query string) tea.Cmd {
	// Reset cell state map
	v.cellStates = make(map[string]*perCellState)
	v.cancels = nil

	var cmds []tea.Cmd

	for _, cell := range v.cells {
		cell.Status = CellRunning
		cell.StartTime = time.Now()
		cell.Content.Reset()
		cell.Tokens = 0
		cell.TPS = 0
		cell.Error = ""

		ctx, cancel := context.WithCancel(context.Background())
		v.cancels = append(v.cancels, cancel)

		model := fmt.Sprintf("%s+%s", v.ctx.CurrentModel, cell.AgentID)
		respChan, errChan := v.ctx.ServerClient.Generate(ctx, model, query)

		state := &perCellState{
			respChan:  respChan,
			errChan:   errChan,
			startTime: cell.StartTime,
		}
		v.cellStates[cell.AgentID] = state

		agentID := cell.AgentID
		cmds = append(cmds, v.nextChunkFrom(agentID, state))
	}

	return tea.Batch(cmds...)
}

func (v *ArenaView) nextChunk(agentID string) tea.Cmd {
	state, ok := v.cellStates[agentID]
	if !ok {
		return nil
	}
	return v.nextChunkFrom(agentID, state)
}

func (v *ArenaView) nextChunkFrom(agentID string, state *perCellState) tea.Cmd {
	return func() tea.Msg {
		for {
			select {
			case resp, ok := <-state.respChan:
				if !ok {
					elapsed := time.Since(state.startTime)
					return arenaCellDoneMsg{agentID: agentID, duration: elapsed, tokens: state.tokens}
				}
				if resp.Response != "" {
					state.tokens++
					return arenaCellChunkMsg{agentID: agentID, content: resp.Response}
				}
				if resp.Done {
					elapsed := time.Since(state.startTime)
					return arenaCellDoneMsg{agentID: agentID, duration: elapsed, tokens: state.tokens}
				}
			case err, ok := <-state.errChan:
				if ok && err != nil {
					return arenaCellErrorMsg{agentID: agentID, err: err}
				}
			}
		}
	}
}

func (v *ArenaView) cancelAll() {
	for _, cancel := range v.cancels {
		cancel()
	}
}

func (v *ArenaView) findCell(agentID string) *ArenaCell {
	for _, c := range v.cells {
		if c.AgentID == agentID {
			return c
		}
	}
	return nil
}

func (v *ArenaView) allDone() bool {
	return len(v.finished) >= len(v.cells)
}

// --- Grid layout ---

func (v *ArenaView) gridDimensions() (cols, rows int) {
	n := len(v.cells)
	cols = 4
	if v.width < 120 {
		cols = 3
	}
	if v.width < 80 {
		cols = 2
	}
	rows = (n + cols - 1) / cols
	return
}

// --- View rendering ---

func (v *ArenaView) View() string {
	headerStyle := lipgloss.NewStyle().
		Bold(true).
		Foreground(ui.ColorPrimary).
		Width(v.width).
		Padding(0, 1)

	switch v.phase {
	case ArenaInput:
		title := headerStyle.Render("Racing Arena  —  Enter a query to race all agents simultaneously")
		hint := lipgloss.NewStyle().Foreground(ui.ColorMuted).Render("  Esc → back to chat")
		return lipgloss.JoinVertical(lipgloss.Left,
			title,
			"",
			"  Query: "+v.input.View(),
			hint,
		)

	case ArenaRacing:
		return v.renderRacing(headerStyle)

	case ArenaSummary:
		return v.renderSummary(headerStyle)
	}

	return ""
}

func (v *ArenaView) renderRacing(headerStyle lipgloss.Style) string {
	queryDisplay := v.query
	if len(queryDisplay) > 50 {
		queryDisplay = queryDisplay[:47] + "..."
	}

	title := headerStyle.Render(fmt.Sprintf("Racing Arena  |  \"%s\"", queryDisplay))
	leaderboard := v.renderLeaderboard()
	grid := v.renderGrid()

	return lipgloss.JoinVertical(lipgloss.Left, title, leaderboard, grid)
}

func (v *ArenaView) renderLeaderboard() string {
	var finished []string
	var running int

	fastestTPS := 0.0
	fastestName := ""

	for _, c := range v.cells {
		switch c.Status {
		case CellDone:
			finished = append(finished, fmt.Sprintf("%s (%.1fs)", c.AgentName, c.Duration.Seconds()))
			if c.TPS > fastestTPS {
				fastestTPS = c.TPS
				fastestName = c.AgentName
			}
		case CellRunning:
			running++
			if c.TPS > fastestTPS {
				fastestTPS = c.TPS
				fastestName = c.AgentName
			}
		}
	}

	doneStr := "none yet"
	if len(finished) > 0 {
		doneStr = strings.Join(finished, " • ")
	}

	tpsStr := "-"
	if fastestName != "" {
		tpsStr = fmt.Sprintf("%s (%.1f)", fastestName, fastestTPS)
	}

	bar := fmt.Sprintf("Finished: %s  |  Running: %d  |  Fastest TPS: %s",
		doneStr, running, tpsStr)

	return lipgloss.NewStyle().
		Foreground(ui.ColorMuted).
		Width(v.width).
		Padding(0, 1).
		Render(bar)
}

func (v *ArenaView) renderGrid() string {
	cols, _ := v.gridDimensions()
	headerHeight := 4 // title + leaderboard + padding
	availH := v.height - headerHeight
	if availH < 6 {
		availH = 6
	}

	rows := (len(v.cells) + cols - 1) / cols
	cellH := availH / rows
	if cellH < 5 {
		cellH = 5
	}
	cellW := (v.width) / cols

	var rowStrings []string
	for r := 0; r < rows; r++ {
		var rowCells []string
		for c := 0; c < cols; c++ {
			idx := r*cols + c
			if idx < len(v.cells) {
				rowCells = append(rowCells, v.renderCell(v.cells[idx], cellW, cellH))
			}
		}
		rowStrings = append(rowStrings, lipgloss.JoinHorizontal(lipgloss.Top, rowCells...))
	}

	return lipgloss.JoinVertical(lipgloss.Left, rowStrings...)
}

func (v *ArenaView) renderCell(cell *ArenaCell, width, height int) string {
	var borderColor lipgloss.Color
	var statusStr string

	switch cell.Status {
	case CellWaiting:
		borderColor = ui.ColorMuted
		statusStr = lipgloss.NewStyle().Foreground(ui.ColorMuted).Render("○ waiting")
	case CellRunning:
		borderColor = ui.ColorPrimary
		statusStr = lipgloss.NewStyle().Foreground(ui.ColorPrimary).Render("● streaming")
	case CellDone:
		borderColor = ui.ColorSuccess
		statusStr = lipgloss.NewStyle().Foreground(ui.ColorSuccess).Render(fmt.Sprintf("✓ %.1fs", cell.Duration.Seconds()))
	case CellError:
		borderColor = ui.ColorError
		statusStr = lipgloss.NewStyle().Foreground(ui.ColorError).Render("✗ error")
	}

	titleLine := fmt.Sprintf("%s  %s",
		lipgloss.NewStyle().Bold(true).Render(cell.AgentName),
		statusStr,
	)

	content := cell.Content.String()
	if cell.Error != "" {
		content = cell.Error
	}

	maxContentLines := height - 4
	if maxContentLines < 1 {
		maxContentLines = 1
	}
	lines := strings.Split(content, "\n")
	// Show last N lines (tail) so we see the newest content
	if len(lines) > maxContentLines {
		lines = lines[len(lines)-maxContentLines:]
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

	metricsLine := ""
	if cell.Status == CellRunning || cell.Status == CellDone {
		metricsLine = lipgloss.NewStyle().Foreground(ui.ColorMuted).
			Render(fmt.Sprintf("%d tok  %.0ftps", cell.Tokens, cell.TPS))
	}

	var parts []string
	parts = append(parts, titleLine)
	parts = append(parts, strings.Join(lines, "\n"))
	if metricsLine != "" {
		parts = append(parts, metricsLine)
	}

	cellContent := strings.Join(parts, "\n")

	style := lipgloss.NewStyle().
		Border(lipgloss.RoundedBorder()).
		BorderForeground(borderColor).
		Width(width - 2).
		Height(height - 2).
		Padding(0, 1)

	return style.Render(cellContent)
}

func (v *ArenaView) renderSummary(headerStyle lipgloss.Style) string {
	title := headerStyle.Render("Arena Summary  |  Enter → re-run  |  Esc → back to chat")

	// Sort cells by finish order
	type ranked struct {
		rank int
		cell *ArenaCell
	}
	var ranked_ []ranked
	finishOrder := map[string]int{}
	for i, id := range v.finished {
		finishOrder[id] = i + 1
	}
	for _, c := range v.cells {
		r, ok := finishOrder[c.AgentID]
		if !ok {
			r = 999
		}
		ranked_ = append(ranked_, ranked{rank: r, cell: c})
	}
	sort.Slice(ranked_, func(i, j int) bool {
		return ranked_[i].rank < ranked_[j].rank
	})

	var sb strings.Builder
	hdr := lipgloss.NewStyle().Bold(true).Foreground(ui.ColorPrimary)
	sb.WriteString(hdr.Render(fmt.Sprintf("  %-4s  %-18s  %-8s  %-8s  %-8s", "Rank", "Agent", "Time", "Tokens", "TPS")))
	sb.WriteString("\n")
	sb.WriteString("  " + strings.Repeat("─", 52) + "\n")

	for _, r := range ranked_ {
		c := r.cell
		rankStr := fmt.Sprintf("%d", r.rank)
		if r.rank == 999 {
			rankStr = "-"
		}
		timeStr := "-"
		tpsStr := "-"
		tokStr := "-"
		if c.Status == CellDone {
			timeStr = fmt.Sprintf("%.2fs", c.Duration.Seconds())
			tokStr = fmt.Sprintf("%d", c.Tokens)
			tpsStr = fmt.Sprintf("%.1f", c.TPS)
		} else if c.Status == CellError {
			timeStr = "error"
		}
		sb.WriteString(fmt.Sprintf("  %-4s  %-18s  %-8s  %-8s  %-8s\n",
			rankStr, c.AgentName, timeStr, tokStr, tpsStr))
	}

	return lipgloss.JoinVertical(lipgloss.Left, title, "", sb.String())
}
