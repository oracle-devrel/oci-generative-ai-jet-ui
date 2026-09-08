package ui

import (
	"fmt"
	"time"

	"github.com/charmbracelet/lipgloss"
)

type MetricsBar struct {
	ttft     time.Duration
	tokens   int
	tps      float64
	duration time.Duration
	model    string
	width    int
	active   bool
}

func NewMetricsBar() *MetricsBar {
	return &MetricsBar{}
}

func (m *MetricsBar) SetTTFT(d time.Duration)    { m.ttft = d; m.active = true }
func (m *MetricsBar) SetTokens(n int)             { m.tokens = n }
func (m *MetricsBar) SetTPS(tps float64)          { m.tps = tps }
func (m *MetricsBar) SetDuration(d time.Duration) { m.duration = d }
func (m *MetricsBar) SetModel(model string)       { m.model = model }
func (m *MetricsBar) SetWidth(w int)              { m.width = w }
func (m *MetricsBar) Reset() {
	m.active = false
	m.tokens = 0
	m.tps = 0
	m.ttft = 0
	m.duration = 0
}

func TPSTier(tps float64) string {
	if tps > 30 {
		return "green"
	}
	if tps > 10 {
		return "yellow"
	}
	return "red"
}

func (m *MetricsBar) View() string {
	if !m.active {
		return ""
	}

	tpsColors := map[string]lipgloss.Color{
		"green":  lipgloss.Color("#00FF00"),
		"yellow": lipgloss.Color("#FFFF00"),
		"red":    lipgloss.Color("#FF0000"),
	}

	tpsColor := tpsColors[TPSTier(m.tps)]

	ttftStr := fmt.Sprintf("TTFT: %dms", m.ttft.Milliseconds())
	tokStr := fmt.Sprintf("Tokens: %d", m.tokens)
	tpsStr := lipgloss.NewStyle().Foreground(tpsColor).Render(fmt.Sprintf("TPS: %.1f", m.tps))
	durStr := fmt.Sprintf("Time: %.1fs", m.duration.Seconds())
	modelStr := lipgloss.NewStyle().Foreground(lipgloss.Color("#FFFF00")).Render(fmt.Sprintf("Model: %s", m.model))

	sep := lipgloss.NewStyle().Foreground(lipgloss.Color("#666666")).Render(" │ ")

	bar := ttftStr + sep + tokStr + sep + tpsStr + sep + durStr + sep + modelStr

	style := lipgloss.NewStyle().
		Width(m.width).
		Foreground(lipgloss.Color("#AAAAAA")).
		PaddingLeft(1)

	return style.Render(bar)
}
