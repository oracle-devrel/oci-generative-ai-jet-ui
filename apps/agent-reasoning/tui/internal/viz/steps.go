package viz

import (
	"fmt"
	"strings"

	"agent-reasoning-tui/internal/client"

	"github.com/charmbracelet/lipgloss"
)

var (
	stepHeaderStyle = lipgloss.NewStyle().
			Foreground(lipgloss.Color("#00FFFF")).
			Bold(true)
	stepBoxStyle = lipgloss.NewStyle().
			Border(lipgloss.RoundedBorder()).
			BorderForeground(lipgloss.Color("#00FFFF")).
			Padding(0, 1)
	finalBoxStyle = lipgloss.NewStyle().
			Border(lipgloss.DoubleBorder()).
			BorderForeground(lipgloss.Color("#00FF00")).
			Padding(0, 1)
	stepSepStyle = lipgloss.NewStyle().Foreground(lipgloss.Color("#444444"))
)

type stepEntry struct {
	label   string
	content string
	isFinal bool
}

// StepsViz renders CoT chain_step events as numbered panels.
type StepsViz struct {
	steps         []stepEntry
	width, height int
}

func NewStepsViz(width, height int) Visualizer {
	return &StepsViz{width: width, height: height}
}

func (v *StepsViz) Reset() {
	v.steps = nil
}

func (v *StepsViz) SetSize(width, height int) {
	v.width = width
	v.height = height
}

func (v *StepsViz) Update(event client.StructuredEvent) {
	switch event.EventType {
	case "chain_step":
		stepNum := getInt(event.Data, "step")
		content := getString(event.Data, "content")
		label := fmt.Sprintf("Step %d", stepNum)
		if stepNum == 0 {
			label = "Step"
		}
		v.steps = append(v.steps, stepEntry{label: label, content: content})

	case "final":
		content := getString(event.Data, "content")
		if content == "" {
			content = getString(event.Data, "answer")
		}
		v.steps = append(v.steps, stepEntry{label: "Answer", content: content, isFinal: true})
	}
}

func (v *StepsViz) View() string {
	if len(v.steps) == 0 {
		return stepSepStyle.Render("Waiting for steps...")
	}

	innerWidth := v.width - 4 // account for border + padding
	if innerWidth < 10 {
		innerWidth = 10
	}

	var parts []string
	for _, s := range v.steps {
		var header string
		if s.isFinal {
			header = lipgloss.NewStyle().Foreground(lipgloss.Color("#00FF00")).Bold(true).Render(s.label)
		} else {
			header = stepHeaderStyle.Render(s.label)
		}

		sep := strings.Repeat("─", innerWidth)
		body := strings.Join([]string{header, sep, wrapText(s.content, innerWidth)}, "\n")

		var boxed string
		if s.isFinal {
			boxed = finalBoxStyle.Width(innerWidth).Render(body)
		} else {
			boxed = stepBoxStyle.Width(innerWidth).Render(body)
		}
		parts = append(parts, boxed)
	}

	return strings.Join(parts, "\n")
}

// wrapText wraps s at width characters (simple word-wrap).
func wrapText(s string, width int) string {
	if width <= 0 || len(s) <= width {
		return s
	}
	var lines []string
	for len(s) > width {
		cut := width
		// Try to break at a space
		for cut > 0 && s[cut-1] != ' ' {
			cut--
		}
		if cut == 0 {
			cut = width
		}
		lines = append(lines, s[:cut])
		s = strings.TrimLeft(s[cut:], " ")
	}
	if s != "" {
		lines = append(lines, s)
	}
	return strings.Join(lines, "\n")
}
