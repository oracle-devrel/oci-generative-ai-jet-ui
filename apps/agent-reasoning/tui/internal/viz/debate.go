package viz

import (
	"fmt"
	"strings"

	"agent-reasoning-tui/internal/client"

	"github.com/charmbracelet/lipgloss"
)

var (
	advocateStyle  = lipgloss.NewStyle().Bold(true).Foreground(lipgloss.Color("#00FFFF"))
	criticStyle    = lipgloss.NewStyle().Bold(true).Foreground(lipgloss.Color("#FF00FF"))
	synthesisStyle = lipgloss.NewStyle().Bold(true).Foreground(lipgloss.Color("#00FF00"))
	debateSepStyle = lipgloss.NewStyle().Foreground(lipgloss.Color("#444444"))
)

type debateRound struct {
	round     int
	advocate  string
	critic    string
	advScore  float64
	critScore float64
}

// DebateViz renders debate_round events as two-column layout.
type DebateViz struct {
	rounds        []debateRound
	synthesis     string
	width, height int
}

func NewDebateViz(width, height int) Visualizer {
	return &DebateViz{width: width, height: height}
}

func (v *DebateViz) Reset() {
	v.rounds = nil
	v.synthesis = ""
}

func (v *DebateViz) SetSize(width, height int) {
	v.width = width
	v.height = height
}

func (v *DebateViz) Update(event client.StructuredEvent) {
	switch event.EventType {
	case "debate_round":
		round := getInt(event.Data, "round")
		advocate := getString(event.Data, "advocate_content")
		if advocate == "" {
			advocate = getString(event.Data, "advocate")
		}
		critic := getString(event.Data, "critic_content")
		if critic == "" {
			critic = getString(event.Data, "critic")
		}
		advScore := getFloat(event.Data, "advocate_score")
		critScore := getFloat(event.Data, "critic_score")

		// Update existing round or add new one
		found := false
		for i, r := range v.rounds {
			if r.round == round {
				v.rounds[i].advocate = advocate
				v.rounds[i].critic = critic
				v.rounds[i].advScore = advScore
				v.rounds[i].critScore = critScore
				found = true
				break
			}
		}
		if !found {
			v.rounds = append(v.rounds, debateRound{
				round: round, advocate: advocate, critic: critic,
				advScore: advScore, critScore: critScore,
			})
		}

	case "final":
		v.synthesis = getString(event.Data, "content")
		if v.synthesis == "" {
			v.synthesis = getString(event.Data, "synthesis")
		}
	}
}

func (v *DebateViz) View() string {
	if len(v.rounds) == 0 {
		return debateSepStyle.Render("Waiting for debate rounds...")
	}

	colWidth := (v.width - 3) / 2
	if colWidth < 10 {
		colWidth = 10
	}

	var lines []string

	// Column headers
	advHeader := advocateStyle.Width(colWidth).Render("Advocate")
	critHeader := criticStyle.Width(colWidth).Render("Critic")
	lines = append(lines, advHeader+" │ "+critHeader)
	lines = append(lines, strings.Repeat("─", colWidth)+"─┼─"+strings.Repeat("─", colWidth))

	for _, r := range v.rounds {
		roundLabel := debateSepStyle.Render(fmt.Sprintf("Round %d", r.round))
		lines = append(lines, roundLabel)

		advScore := ""
		if r.advScore > 0 {
			advScore = fmt.Sprintf(" [%.2f]", r.advScore)
		}
		critScore := ""
		if r.critScore > 0 {
			critScore = fmt.Sprintf(" [%.2f]", r.critScore)
		}

		advContent := truncateStr(r.advocate+advScore, colWidth)
		critContent := truncateStr(r.critic+critScore, colWidth)

		advCell := lipgloss.NewStyle().Foreground(lipgloss.Color("#00FFFF")).Width(colWidth).Render(advContent)
		critCell := lipgloss.NewStyle().Foreground(lipgloss.Color("#FF00FF")).Width(colWidth).Render(critContent)
		lines = append(lines, advCell+" │ "+critCell)
	}

	if v.synthesis != "" {
		lines = append(lines, "")
		lines = append(lines, synthesisStyle.Render("Synthesis:"))
		lines = append(lines, wrapText(v.synthesis, v.width-2))
	}

	return strings.Join(lines, "\n")
}
