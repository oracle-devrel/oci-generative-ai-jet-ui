package ui

import (
	"fmt"
	"strings"

	"github.com/charmbracelet/lipgloss"
)

var (
	progressFilledStyle = lipgloss.NewStyle().Foreground(lipgloss.Color("#00FF00"))
	progressEmptyStyle  = lipgloss.NewStyle().Foreground(lipgloss.Color("#666666"))
	progressLabelStyle  = lipgloss.NewStyle().Foreground(lipgloss.Color("#00FFFF")).Bold(true)
)

// ProgressBar is a labeled progress bar with stages.
type ProgressBar struct {
	stages  []string
	current int
	width   int
}

func NewProgressBar(stages []string, width int) *ProgressBar {
	return &ProgressBar{stages: stages, width: width}
}

// SetCurrent sets the current stage index (0-based).
func (p *ProgressBar) SetCurrent(stage int) {
	p.current = stage
}

// View renders: [████░░░░░░] Stage 2/5: Clarity
func (p *ProgressBar) View() string {
	n := len(p.stages)
	if n == 0 {
		return ""
	}

	// Bar width: total width minus label space "[ ] Stage N/N: "
	// Reserve ~20 chars for brackets and label prefix
	barWidth := p.width - 20
	if barWidth < 4 {
		barWidth = 4
	}

	// How many blocks filled?
	idx := p.current
	if idx < 0 {
		idx = 0
	}
	if idx >= n {
		idx = n - 1
	}
	filled := 0
	if n > 0 {
		filled = int(float64(idx+1) / float64(n) * float64(barWidth))
	}
	if filled > barWidth {
		filled = barWidth
	}

	var barSb strings.Builder
	barSb.WriteString("[")
	for i := 0; i < barWidth; i++ {
		if i < filled {
			barSb.WriteString(progressFilledStyle.Render("█"))
		} else {
			barSb.WriteString(progressEmptyStyle.Render("░"))
		}
	}
	barSb.WriteString("]")

	stageName := p.stages[idx]
	label := progressLabelStyle.Render(fmt.Sprintf(" Stage %d/%d: %s", idx+1, n, stageName))

	return barSb.String() + label
}
