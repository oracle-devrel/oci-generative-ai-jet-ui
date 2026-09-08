package ui

import (
	"fmt"
	"strings"

	"github.com/charmbracelet/lipgloss"
)

// Iteration holds one refinement pass.
type Iteration struct {
	Content string
	Score   float64
}

var (
	gaugeFilledAbove = lipgloss.NewStyle().Foreground(lipgloss.Color("#00FF00"))
	gaugeFilledBelow = lipgloss.NewStyle().Foreground(lipgloss.Color("#FFFF00"))
	gaugeEmpty       = lipgloss.NewStyle().Foreground(lipgloss.Color("#666666"))
	diffHeaderStyle  = lipgloss.NewStyle().Bold(true).Foreground(lipgloss.Color("#00FFFF"))
)

// DiffView renders iterations with score gauges.
type DiffView struct {
	iterations    []Iteration
	threshold     float64
	width, height int
}

func NewDiffView(width, height int) *DiffView {
	return &DiffView{width: width, height: height, threshold: 0.9}
}

// SetThreshold updates the score threshold.
func (d *DiffView) SetThreshold(t float64) {
	d.threshold = t
}

// AddIteration appends a new content+score pair.
func (d *DiffView) AddIteration(content string, score float64) {
	d.iterations = append(d.iterations, Iteration{Content: content, Score: score})
}

// View renders stacked iterations with score gauge bars.
func (d *DiffView) View() string {
	if len(d.iterations) == 0 {
		return ""
	}

	// Gauge width: leave room for label "Iter N: [gauge] 0.00"
	gaugeWidth := d.width - 20
	if gaugeWidth < 5 {
		gaugeWidth = 5
	}

	var blocks []string
	linesBudget := d.height
	for i, it := range d.iterations {
		if linesBudget <= 0 {
			break
		}
		header := diffHeaderStyle.Render(fmt.Sprintf("Iter %d:", i+1))
		gauge := renderGauge(it.Score, d.threshold, gaugeWidth)
		scoreTxt := fmt.Sprintf(" %.2f", it.Score)
		topLine := header + " " + gauge + scoreTxt

		// Content line — truncate to width
		contentLine := truncateStr(it.Content, d.width)

		blocks = append(blocks, topLine, contentLine)
		linesBudget -= 2
		if i < len(d.iterations)-1 {
			blocks = append(blocks, strings.Repeat("─", d.width))
			linesBudget--
		}
	}
	return strings.Join(blocks, "\n")
}

// renderGauge builds a ████░░░░ bar with threshold marker.
func renderGauge(score, threshold float64, width int) string {
	if score < 0 {
		score = 0
	}
	if score > 1 {
		score = 1
	}
	filled := int(score * float64(width))
	threshPos := int(threshold * float64(width))

	var sb strings.Builder
	atOrAbove := score >= threshold
	for i := 0; i < width; i++ {
		if i == threshPos && threshPos < width {
			sb.WriteRune('│')
			continue
		}
		if i < filled {
			ch := "█"
			if atOrAbove {
				sb.WriteString(gaugeFilledAbove.Render(ch))
			} else {
				sb.WriteString(gaugeFilledBelow.Render(ch))
			}
		} else {
			sb.WriteString(gaugeEmpty.Render("░"))
		}
	}
	return sb.String()
}
