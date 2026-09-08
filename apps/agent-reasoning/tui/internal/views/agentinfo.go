package views

import (
	"fmt"
	"strings"

	"agent-reasoning-tui/internal/app"
	"agent-reasoning-tui/internal/ui"

	"github.com/charmbracelet/bubbles/key"
	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"
)

// AgentInfoView shows reference cards for each agent, one at a time.
type AgentInfoView struct {
	ctx      *app.Context
	selected int
	width    int
	height   int
	keys     KeyMap
}

func NewAgentInfoView(appCtx *app.Context) *AgentInfoView {
	return &AgentInfoView{
		ctx:  appCtx,
		keys: defaultKeyMap(),
	}
}

func (v *AgentInfoView) ID() app.ViewID { return app.ViewAgentInfo }

func (v *AgentInfoView) Init() tea.Cmd {
	v.selected = 0
	return nil
}

func (v *AgentInfoView) SetSize(width, height int) {
	v.width = width
	v.height = height
}

func (v *AgentInfoView) Update(msg tea.Msg) (app.View, tea.Cmd) {
	switch msg := msg.(type) {
	case tea.KeyMsg:
		return v.handleKey(msg)
	}
	return v, nil
}

func (v *AgentInfoView) handleKey(msg tea.KeyMsg) (app.View, tea.Cmd) {
	agents := v.agents()

	switch {
	case key.Matches(msg, v.keys.Escape):
		return v, func() tea.Msg { return app.SwitchViewMsg{Target: app.ViewChat} }

	case key.Matches(msg, v.keys.Up):
		if v.selected > 0 {
			v.selected--
		}

	case key.Matches(msg, v.keys.Down):
		if v.selected < len(agents)-1 {
			v.selected++
		}

	case key.Matches(msg, v.keys.Enter):
		if len(agents) > 0 {
			v.ctx.CurrentAgent = agents[v.selected].ID
		}
		return v, func() tea.Msg { return app.SwitchViewMsg{Target: app.ViewChat} }
	}

	return v, nil
}

func (v *AgentInfoView) View() string {
	agents := v.agents()
	if len(agents) == 0 {
		return lipgloss.NewStyle().Foreground(ui.ColorMuted).Padding(2, 3).
			Render("No agent metadata available.\nMake sure the server is running.")
	}

	idx := v.selected
	if idx >= len(agents) {
		idx = len(agents) - 1
	}
	agent := agents[idx]

	cardWidth := v.width - 4
	if cardWidth < 40 {
		cardWidth = 40
	}

	// --- Card sections ---
	bold := lipgloss.NewStyle().Bold(true).Foreground(ui.ColorPrimary)
	muted := lipgloss.NewStyle().Foreground(ui.ColorMuted)
	normal := lipgloss.NewStyle().Foreground(ui.ColorWhite)

	var sb strings.Builder

	// Title row
	refStr := ""
	if agent.Reference != "" {
		refStr = muted.Render("  " + agent.Reference)
	}
	sb.WriteString(bold.Render(agent.Name) + refStr + "\n\n")

	// Description
	if agent.Description != "" {
		sb.WriteString(bold.Render("How it works") + "\n")
		sb.WriteString(normal.Render(wordWrap(agent.Description, cardWidth-4)) + "\n\n")
	}

	// Best for
	if agent.BestFor != "" {
		sb.WriteString(bold.Render("Best for") + "\n")
		sb.WriteString(normal.Render(wordWrap(agent.BestFor, cardWidth-4)) + "\n\n")
	}

	// Parameters
	if len(agent.Parameters) > 0 {
		sb.WriteString(bold.Render("Parameters") + "\n")
		for name, p := range agent.Parameters {
			desc := ""
			if p.Description != "" {
				desc = "  (" + p.Description + ")"
			}
			line := fmt.Sprintf("  %s: %.4g%s", name, p.Default, desc)
			sb.WriteString(normal.Render(line) + "\n")
		}
		sb.WriteString("\n")
	}

	// Tradeoffs
	if agent.Tradeoffs != "" {
		sb.WriteString(bold.Render("Trade-offs") + "\n")
		sb.WriteString(normal.Render(wordWrap(agent.Tradeoffs, cardWidth-4)) + "\n\n")
	}

	cardStyle := lipgloss.NewStyle().
		Border(lipgloss.RoundedBorder()).
		BorderForeground(ui.ColorPrimary).
		Width(cardWidth).
		Padding(1, 2)

	card := cardStyle.Render(sb.String())

	// Navigation strip
	navLine := fmt.Sprintf("  %d / %d", idx+1, len(agents))
	nav := muted.Render(navLine)
	help := muted.Render("  [j/k] navigate  [Enter] select agent  [Esc] back")

	// Sidebar of agent names
	sidebar := v.renderSideBar(agents, idx)

	layout := lipgloss.JoinHorizontal(lipgloss.Top, sidebar, card)

	return lipgloss.JoinVertical(lipgloss.Left, layout, "", nav, help)
}

func (v *AgentInfoView) renderSideBar(agents []app.AgentInfo, selected int) string {
	var rows []string
	for i, a := range agents {
		label := a.Name
		if len(label) > 18 {
			label = label[:15] + "..."
		}
		if i == selected {
			rows = append(rows, lipgloss.NewStyle().
				Bold(true).
				Foreground(ui.ColorPrimary).
				Render("▶ "+label))
		} else {
			rows = append(rows, lipgloss.NewStyle().
				Foreground(ui.ColorMuted).
				Render("  "+label))
		}
	}

	return lipgloss.NewStyle().
		Width(22).
		BorderStyle(lipgloss.NormalBorder()).
		BorderRight(true).
		BorderForeground(ui.ColorMuted).
		Padding(1, 1).
		Render(strings.Join(rows, "\n"))
}

// agents returns ctx.Agents or an empty slice.
func (v *AgentInfoView) agents() []app.AgentInfo {
	if v.ctx != nil {
		return v.ctx.Agents
	}
	return nil
}

// wordWrap wraps text at word boundaries up to maxWidth characters.
func wordWrap(text string, maxWidth int) string {
	if maxWidth <= 0 {
		return text
	}
	words := strings.Fields(text)
	var lines []string
	var current strings.Builder

	for _, word := range words {
		if current.Len() == 0 {
			current.WriteString(word)
		} else if current.Len()+1+len(word) <= maxWidth {
			current.WriteString(" ")
			current.WriteString(word)
		} else {
			lines = append(lines, current.String())
			current.Reset()
			current.WriteString(word)
		}
	}
	if current.Len() > 0 {
		lines = append(lines, current.String())
	}
	return strings.Join(lines, "\n")
}
