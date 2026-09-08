package views

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"time"

	"agent-reasoning-tui/internal/app"
	"agent-reasoning-tui/internal/session"

	"github.com/charmbracelet/bubbles/key"
	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"
)

// sessionsLoadedMsg carries sessions from the async load.
type sessionsLoadedMsg struct{ sessions []session.Session }

// sessionsErrorMsg carries a load error.
type sessionsErrorMsg struct{ err error }

// sessionsDeletedMsg signals a successful delete.
type sessionsDeletedMsg struct{ id string }

// sessionsExportedMsg signals a successful markdown export.
type sessionsExportedMsg struct{ path string }

// SessionsView lets users browse, filter, and act on past sessions.
type SessionsView struct {
	ctx      *app.Context
	sessions []session.Session
	filtered []session.Session
	selected int

	filterText  string
	filterType  session.SessionType // "" means all
	filterFocus bool               // true = typing in filter box

	// Detail / confirmation overlay
	detailActive  bool
	detailContent string
	confirmDelete bool
	statusMsg     string
	statusExpiry  time.Time

	width  int
	height int
}

// NewSessionsView creates a SessionsView.
func NewSessionsView(ctx *app.Context) *SessionsView {
	return &SessionsView{ctx: ctx}
}

func (v *SessionsView) ID() app.ViewID { return app.ViewSessions }

func (v *SessionsView) Init() tea.Cmd {
	return v.loadSessions()
}

func (v *SessionsView) SetSize(width, height int) {
	v.width = width
	v.height = height
}

// --- Update ---

func (v *SessionsView) Update(msg tea.Msg) (app.View, tea.Cmd) {
	switch msg := msg.(type) {
	case sessionsLoadedMsg:
		v.sessions = msg.sessions
		v.applyFilter()

	case sessionsErrorMsg:
		v.setStatus("Error loading sessions: " + msg.err.Error())

	case sessionsDeletedMsg:
		// Remove from local slices.
		v.sessions = removeByID(v.sessions, msg.id)
		v.applyFilter()
		if v.selected >= len(v.filtered) {
			v.selected = len(v.filtered) - 1
		}
		if v.selected < 0 {
			v.selected = 0
		}
		v.setStatus("Session deleted.")

	case sessionsExportedMsg:
		v.setStatus("Exported to " + msg.path)

	case tea.KeyMsg:
		return v.handleKey(msg)
	}

	return v, nil
}

func (v *SessionsView) handleKey(msg tea.KeyMsg) (app.View, tea.Cmd) {
	// Detail overlay — any key closes it.
	if v.detailActive {
		v.detailActive = false
		return v, nil
	}

	// Delete confirmation overlay.
	if v.confirmDelete {
		switch msg.String() {
		case "y", "Y", "enter":
			if len(v.filtered) > 0 {
				id := v.filtered[v.selected].ID
				store := v.ctx.SessionStore
				return v, func() tea.Msg {
					if err := store.Delete(id); err != nil {
						return sessionsErrorMsg{err: err}
					}
					return sessionsDeletedMsg{id: id}
				}
			}
		}
		v.confirmDelete = false
		return v, nil
	}

	// Filter text box active.
	if v.filterFocus {
		switch msg.String() {
		case "esc", "enter":
			v.filterFocus = false
		case "backspace":
			if len(v.filterText) > 0 {
				v.filterText = v.filterText[:len(v.filterText)-1]
				v.applyFilter()
				v.selected = 0
			}
		default:
			if len(msg.String()) == 1 {
				v.filterText += msg.String()
				v.applyFilter()
				v.selected = 0
			}
		}
		return v, nil
	}

	switch {
	case msg.String() == "esc":
		return v, func() tea.Msg { return app.SwitchViewMsg{Target: app.ViewChat} }

	case msg.String() == "j" || msg.String() == "down":
		if v.selected < len(v.filtered)-1 {
			v.selected++
		}

	case msg.String() == "k" || msg.String() == "up":
		if v.selected > 0 {
			v.selected--
		}

	case key.Matches(msg, key.NewBinding(key.WithKeys("/"))):
		v.filterFocus = true

	case msg.String() == "1":
		v.filterType = ""
		v.applyFilter()
		v.selected = 0

	case msg.String() == "2":
		v.filterType = session.TypeChat
		v.applyFilter()
		v.selected = 0

	case msg.String() == "3":
		v.filterType = session.TypeArena
		v.applyFilter()
		v.selected = 0

	case msg.String() == "4":
		v.filterType = session.TypeDuel
		v.applyFilter()
		v.selected = 0

	case msg.String() == "enter":
		if len(v.filtered) > 0 {
			s := v.filtered[v.selected]
			v.detailContent = v.ctx.SessionStore.ExportMarkdown(s)
			v.detailActive = true
		}

	case msg.String() == "r":
		// Re-run: switch to chat with query pre-filled.
		if len(v.filtered) > 0 {
			s := v.filtered[v.selected]
			v.ctx.CurrentAgent = s.Strategy
			// Signal chat view to pre-fill query via context.
			v.ctx.PendingQuery = s.Query
			return v, func() tea.Msg { return app.SwitchViewMsg{Target: app.ViewChat} }
		}

	case msg.String() == "d":
		if len(v.filtered) > 0 {
			v.confirmDelete = true
		}

	case msg.String() == "x":
		if len(v.filtered) > 0 {
			s := v.filtered[v.selected]
			store := v.ctx.SessionStore
			projectDir := v.ctx.ProjectDir
			return v, func() tea.Msg {
				md := store.ExportMarkdown(s)
				dir := filepath.Join(projectDir, "data", "exports")
				os.MkdirAll(dir, 0755)
				path := filepath.Join(dir, s.ID+".md")
				if err := os.WriteFile(path, []byte(md), 0644); err != nil {
					return sessionsErrorMsg{err: err}
				}
				return sessionsExportedMsg{path: path}
			}
		}
	}

	return v, nil
}

// --- View ---

func (v *SessionsView) View() string {
	if v.width == 0 {
		return "Loading sessions..."
	}

	// Status message (expires after 3 seconds).
	status := ""
	if !v.statusExpiry.IsZero() && time.Now().Before(v.statusExpiry) {
		status = v.statusMsg
	}

	// Detail overlay.
	if v.detailActive {
		return v.renderDetailOverlay()
	}

	// Delete confirmation overlay.
	if v.confirmDelete {
		return v.renderConfirmOverlay()
	}

	leftWidth := 20
	rightWidth := v.width - leftWidth - 3
	if rightWidth < 20 {
		rightWidth = 20
	}
	listHeight := v.height - 6

	// Left panel: filter + type selector.
	leftPanel := v.renderLeftPanel(leftWidth, listHeight)

	// Right panel: session list.
	rightPanel := v.renderRightPanel(rightWidth, listHeight)

	// Join panels.
	main := lipgloss.JoinHorizontal(lipgloss.Top, leftPanel, " ", rightPanel)

	// Footer.
	footerStyle := lipgloss.NewStyle().
		Foreground(lipgloss.Color("240")).
		Width(v.width).
		Padding(0, 1)
	footer := footerStyle.Render("[Enter] View  [r] Re-run  [d] Delete  [x] Export  [/] Filter  [1-4] Type  [Esc] Back")

	var parts []string
	parts = append(parts, main)
	if status != "" {
		parts = append(parts, lipgloss.NewStyle().Foreground(lipgloss.Color("10")).Render(status))
	}
	parts = append(parts, footer)

	return lipgloss.JoinVertical(lipgloss.Left, parts...)
}

func (v *SessionsView) renderLeftPanel(width, height int) string {
	style := lipgloss.NewStyle().
		Border(lipgloss.RoundedBorder()).
		BorderForeground(lipgloss.Color("240")).
		Width(width).
		Height(height).
		Padding(0, 1)

	cursor := "▌"
	if !v.filterFocus {
		cursor = " "
	}

	filterLine := fmt.Sprintf("Filter:\n> %s%s", v.filterText, cursor)

	types := []struct {
		label string
		t     session.SessionType
	}{
		{"All", ""},
		{"Chat", session.TypeChat},
		{"Arena", session.TypeArena},
		{"Duel", session.TypeDuel},
	}

	typeLines := "\nType:"
	for i, t := range types {
		sel := "○"
		if v.filterType == t.t {
			sel = "●"
		}
		typeLines += fmt.Sprintf("\n%s %s  [%d]", sel, t.label, i+1)
	}

	content := filterLine + typeLines
	return style.Render(content)
}

func (v *SessionsView) renderRightPanel(width, height int) string {
	style := lipgloss.NewStyle().
		Border(lipgloss.RoundedBorder()).
		BorderForeground(lipgloss.Color("240")).
		Width(width).
		Height(height)

	if len(v.filtered) == 0 {
		return style.Render(lipgloss.NewStyle().
			Foreground(lipgloss.Color("240")).
			Padding(1, 2).
			Render("No sessions found."))
	}

	selectedStyle := lipgloss.NewStyle().
		Background(lipgloss.Color("62")).
		Foreground(lipgloss.Color("230")).
		Width(width - 2)

	normalStyle := lipgloss.NewStyle().
		Width(width - 2)

	maxVisible := height - 2
	if maxVisible < 1 {
		maxVisible = 1
	}

	start := 0
	if v.selected >= maxVisible {
		start = v.selected - maxVisible + 1
	}
	end := start + maxVisible
	if end > len(v.filtered) {
		end = len(v.filtered)
	}

	var lines []string
	for i := start; i < end; i++ {
		s := v.filtered[i]
		ts := s.Timestamp.Format("2006-01-02 15:04")
		strategy := padRight(string(s.Strategy), 8)
		query := s.Query
		maxQ := width - 30
		if maxQ < 10 {
			maxQ = 10
		}
		if len(query) > maxQ {
			query = query[:maxQ-2] + ".."
		}
		line := fmt.Sprintf("  %s  %-8s  %s", ts, strategy, query)
		if i == v.selected {
			lines = append(lines, selectedStyle.Render(line))
		} else {
			lines = append(lines, normalStyle.Render(line))
		}
	}

	return style.Render(strings.Join(lines, "\n"))
}

func (v *SessionsView) renderDetailOverlay() string {
	boxStyle := lipgloss.NewStyle().
		Border(lipgloss.RoundedBorder()).
		BorderForeground(lipgloss.Color("63")).
		Padding(1, 2).
		Width(v.width - 4).
		Height(v.height - 4)

	content := v.detailContent
	maxLen := (v.width - 8) * (v.height - 8)
	if len(content) > maxLen && maxLen > 0 {
		content = content[:maxLen] + "\n..."
	}

	footer := lipgloss.NewStyle().Foreground(lipgloss.Color("240")).Render("\n[any key] Close")
	return lipgloss.Place(v.width, v.height, lipgloss.Center, lipgloss.Center,
		boxStyle.Render(content+footer))
}

func (v *SessionsView) renderConfirmOverlay() string {
	if len(v.filtered) == 0 {
		v.confirmDelete = false
		return v.View()
	}
	s := v.filtered[v.selected]
	msg := fmt.Sprintf("Delete session %q? [y/Enter] Yes  [any other] No", s.ID)
	boxStyle := lipgloss.NewStyle().
		Border(lipgloss.RoundedBorder()).
		BorderForeground(lipgloss.Color("9")).
		Padding(1, 2)
	return lipgloss.Place(v.width, v.height, lipgloss.Center, lipgloss.Center,
		boxStyle.Render(msg))
}

// --- Helpers ---

func (v *SessionsView) loadSessions() tea.Cmd {
	store := v.ctx.SessionStore
	if store == nil {
		return nil
	}
	return func() tea.Msg {
		sessions, err := store.List()
		if err != nil {
			return sessionsErrorMsg{err: err}
		}
		return sessionsLoadedMsg{sessions: sessions}
	}
}

func (v *SessionsView) applyFilter() {
	v.filtered = nil
	for _, s := range v.sessions {
		if v.filterType != "" && s.Type != v.filterType {
			continue
		}
		if v.filterText != "" && !strings.Contains(strings.ToLower(s.Query), strings.ToLower(v.filterText)) {
			continue
		}
		v.filtered = append(v.filtered, s)
	}
}

func (v *SessionsView) setStatus(msg string) {
	v.statusMsg = msg
	v.statusExpiry = time.Now().Add(3 * time.Second)
}

func removeByID(sessions []session.Session, id string) []session.Session {
	out := sessions[:0]
	for _, s := range sessions {
		if s.ID != id {
			out = append(out, s)
		}
	}
	return out
}

func padRight(s string, n int) string {
	if len(s) >= n {
		return s[:n]
	}
	return s + strings.Repeat(" ", n-len(s))
}
