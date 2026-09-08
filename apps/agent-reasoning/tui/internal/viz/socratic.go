package viz

import (
	"strings"

	"agent-reasoning-tui/internal/client"

	"github.com/charmbracelet/lipgloss"
)

var (
	socraticQStyle = lipgloss.NewStyle().Bold(true).Foreground(lipgloss.Color("#00FFFF"))
	socraticAStyle = lipgloss.NewStyle().Foreground(lipgloss.Color("#CCCCCC"))
	socraticFStyle = lipgloss.NewStyle().Bold(true).Foreground(lipgloss.Color("#00FF00"))
)

type socraticEntry struct {
	question string
	answer   string
	isFinal  bool
}

// SocraticViz renders Socratic dialogue Q&A events.
type SocraticViz struct {
	entries       []socraticEntry
	width, height int
}

func NewSocraticViz(width, height int) Visualizer {
	return &SocraticViz{width: width, height: height}
}

func (v *SocraticViz) Reset() {
	v.entries = nil
}

func (v *SocraticViz) SetSize(width, height int) {
	v.width = width
	v.height = height
}

func (v *SocraticViz) Update(event client.StructuredEvent) {
	switch event.EventType {
	case "socratic":
		question := getString(event.Data, "question")
		answer := getString(event.Data, "answer")
		isFinalSynth := getBool(event.Data, "is_final_synthesis")

		v.entries = append(v.entries, socraticEntry{
			question: question,
			answer:   answer,
			isFinal:  isFinalSynth,
		})

	case "final":
		content := getString(event.Data, "content")
		if content != "" {
			v.entries = append(v.entries, socraticEntry{
				question: "Final Synthesis",
				answer:   content,
				isFinal:  true,
			})
		}
	}
}

func (v *SocraticViz) View() string {
	if len(v.entries) == 0 {
		return socraticAStyle.Render("Waiting for dialogue...")
	}

	var lines []string
	indent := "  "

	for _, e := range v.entries {
		if e.isFinal {
			lines = append(lines, socraticFStyle.Render("◆ "+e.question))
		} else {
			lines = append(lines, socraticQStyle.Render("? "+e.question))
		}
		if e.answer != "" {
			// Indent answer lines
			answerLines := strings.Split(wrapText(e.answer, v.width-4), "\n")
			for _, al := range answerLines {
				lines = append(lines, socraticAStyle.Render(indent+al))
			}
		}
		lines = append(lines, "")
	}

	return strings.Join(lines, "\n")
}
