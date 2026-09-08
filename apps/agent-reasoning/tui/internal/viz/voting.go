package viz

import (
	"fmt"
	"strings"

	"agent-reasoning-tui/internal/client"

	"github.com/charmbracelet/lipgloss"
)

var (
	votingHeaderStyle = lipgloss.NewStyle().Bold(true).Foreground(lipgloss.Color("#00FFFF"))
	votingSepStyle    = lipgloss.NewStyle().Foreground(lipgloss.Color("#444444"))
	voteBarFilled     = lipgloss.NewStyle().Foreground(lipgloss.Color("#00FF00"))
	voteBarEmpty      = lipgloss.NewStyle().Foreground(lipgloss.Color("#666666"))
)

type sampleEntry struct {
	id      int
	content string
	answer  string
}

// VotingViz renders Consistency sample events as side-by-side columns.
type VotingViz struct {
	samples       []sampleEntry
	finalAnswer   string
	width, height int
}

func NewVotingViz(width, height int) Visualizer {
	return &VotingViz{width: width, height: height}
}

func (v *VotingViz) Reset() {
	v.samples = nil
	v.finalAnswer = ""
}

func (v *VotingViz) SetSize(width, height int) {
	v.width = width
	v.height = height
}

func (v *VotingViz) Update(event client.StructuredEvent) {
	switch event.EventType {
	case "sample":
		id := getInt(event.Data, "id")
		content := getString(event.Data, "content")
		answer := getString(event.Data, "answer")
		v.samples = append(v.samples, sampleEntry{id: id, content: content, answer: answer})

	case "final":
		v.finalAnswer = getString(event.Data, "answer")
		if v.finalAnswer == "" {
			v.finalAnswer = getString(event.Data, "content")
		}
	}
}

func (v *VotingViz) View() string {
	if len(v.samples) == 0 {
		return votingSepStyle.Render("Waiting for samples...")
	}

	n := len(v.samples)
	if n == 0 {
		return ""
	}

	colWidth := (v.width - (n - 1)) / n
	if colWidth < 8 {
		colWidth = 8
	}

	// Build header row
	headers := make([]string, n)
	seps := make([]string, n)
	contents := make([]string, n)

	for i, s := range v.samples {
		headers[i] = votingHeaderStyle.Width(colWidth).Render(
			truncateStr(fmt.Sprintf("Sample %d", s.id+1), colWidth),
		)
		seps[i] = strings.Repeat("─", colWidth)
		contents[i] = lipgloss.NewStyle().Width(colWidth).Render(
			truncateStr(s.content, colWidth),
		)
	}

	var lines []string
	lines = append(lines, strings.Join(headers, " "))
	lines = append(lines, strings.Join(seps, " "))
	lines = append(lines, strings.Join(contents, " "))

	// Vote tally if we have a final answer
	if v.finalAnswer != "" {
		// Count votes by answer
		tally := make(map[string]int)
		for _, s := range v.samples {
			if s.answer != "" {
				tally[s.answer]++
			}
		}

		lines = append(lines, "")
		lines = append(lines, votingHeaderStyle.Render("Vote Tally:"))

		barWidth := v.width - 30
		if barWidth < 5 {
			barWidth = 5
		}

		for answer, count := range tally {
			filled := int(float64(count) / float64(n) * float64(barWidth))
			var bar strings.Builder
			for i := 0; i < barWidth; i++ {
				if i < filled {
					bar.WriteString(voteBarFilled.Render("█"))
				} else {
					bar.WriteString(voteBarEmpty.Render("░"))
				}
			}
			label := truncateStr(answer, 15)
			lines = append(lines, fmt.Sprintf("  %-15s %s %d", label, bar.String(), count))
		}

		lines = append(lines, "")
		lines = append(lines, votingHeaderStyle.Render("Winner: ")+v.finalAnswer)
	}

	return strings.Join(lines, "\n")
}

func truncateStr(s string, width int) string {
	runes := []rune(s)
	if len(runes) > width {
		return string(runes[:width])
	}
	return s
}
