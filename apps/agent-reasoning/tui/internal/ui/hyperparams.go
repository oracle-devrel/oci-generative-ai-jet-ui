package ui

import (
	"fmt"
	"math"
	"sort"
	"strings"

	"agent-reasoning-tui/internal/app"

	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"
)

// ParamEntry holds one tunable hyperparameter with its current and default values.
type ParamEntry struct {
	Name        string
	Description string
	Type        string
	Value       float64
	Default     float64
	Min         float64
	Max         float64
}

// HyperParams is a modal overlay for editing agent hyperparameters.
type HyperParams struct {
	agentName string
	params    []ParamEntry
	selected  int
	active    bool
	width     int
	height    int
}

// NewHyperParams creates an inactive HyperParams overlay.
func NewHyperParams() *HyperParams {
	return &HyperParams{}
}

// Open activates the overlay for the given agent and its parameter schemas.
func (h *HyperParams) Open(agentName string, schemas map[string]app.ParameterSchema) {
	h.agentName = agentName
	h.selected = 0
	h.active = true

	// Sort parameter names for stable ordering
	names := make([]string, 0, len(schemas))
	for n := range schemas {
		names = append(names, n)
	}
	sort.Strings(names)

	h.params = make([]ParamEntry, 0, len(names))
	for _, name := range names {
		p := schemas[name]
		h.params = append(h.params, ParamEntry{
			Name:        name,
			Description: p.Description,
			Type:        p.Type,
			Value:       p.Default,
			Default:     p.Default,
			Min:         p.Min,
			Max:         p.Max,
		})
	}
}

// Close deactivates the overlay.
func (h *HyperParams) Close() {
	h.active = false
}

// Active reports whether the overlay is currently visible.
func (h *HyperParams) Active() bool {
	return h.active
}

// SetSize updates the overlay's position/size hint.
func (h *HyperParams) SetSize(width, height int) {
	h.width = width
	h.height = height
}

// Update handles keyboard input when the overlay is active.
// Returns (applied, values) where applied=true means the user confirmed.
func (h *HyperParams) Update(msg tea.KeyMsg) (applied bool, values map[string]float64) {
	if !h.active || len(h.params) == 0 {
		return false, nil
	}

	switch msg.String() {
	case "j", "down":
		if h.selected < len(h.params)-1 {
			h.selected++
		}

	case "k", "up":
		if h.selected > 0 {
			h.selected--
		}

	case "h", "left":
		h.adjustSelected(-1)

	case "l", "right":
		h.adjustSelected(+1)

	case "r":
		for i := range h.params {
			h.params[i].Value = h.params[i].Default
		}

	case "enter":
		h.active = false
		out := make(map[string]float64, len(h.params))
		for _, p := range h.params {
			out[p.Name] = p.Value
		}
		return true, out

	case "esc":
		h.active = false
	}

	return false, nil
}

func (h *HyperParams) adjustSelected(dir int) {
	if h.selected < 0 || h.selected >= len(h.params) {
		return
	}
	p := &h.params[h.selected]
	step := 1.0
	if p.Type == "float" {
		step = 0.1
	}
	newVal := p.Value + float64(dir)*step
	// Snap float to 1 decimal
	if p.Type == "float" {
		newVal = math.Round(newVal*10) / 10
	}
	if newVal < p.Min {
		newVal = p.Min
	}
	if newVal > p.Max {
		newVal = p.Max
	}
	p.Value = newVal
}

// View renders the modal overlay as a string. Caller is responsible for
// placing it on screen with placeOverlay.
func (h *HyperParams) View() string {
	if !h.active {
		return ""
	}

	title := lipgloss.NewStyle().Bold(true).Foreground(ColorPrimary).
		Render(fmt.Sprintf(" %s Parameters ", h.agentName))

	var rows []string
	rows = append(rows, title, "")

	for i, p := range h.params {
		nameStyle := lipgloss.NewStyle().Foreground(ColorWhite)
		descStyle := lipgloss.NewStyle().Foreground(ColorMuted)

		nameLine := nameStyle.Render(fmt.Sprintf("  %s", p.Name))
		if p.Description != "" {
			nameLine += "  " + descStyle.Render(p.Description)
		}
		rows = append(rows, nameLine)

		// Slider row
		valStr := fmtVal(p.Value, p.Type)
		rangeStr := fmt.Sprintf("[%.4g .. %.4g]", p.Min, p.Max)

		var sliderLine string
		if i == h.selected {
			sliderLine = lipgloss.NewStyle().
				Bold(true).
				Foreground(ColorPrimary).
				Render(fmt.Sprintf("  ◀── %s ──▶    %s", valStr, rangeStr))
		} else {
			sliderLine = lipgloss.NewStyle().
				Foreground(ColorMuted).
				Render(fmt.Sprintf("      %s          %s", valStr, rangeStr))
		}
		rows = append(rows, sliderLine, "")
	}

	rows = append(rows, lipgloss.NewStyle().Foreground(ColorMuted).
		Render("  [j/k] select  [h/l] adjust  [Enter] apply  [r] reset  [Esc] cancel"))

	content := strings.Join(rows, "\n")

	// Calculate width needed
	modalW := 50
	for _, r := range rows {
		w := lipgloss.Width(r) + 4
		if w > modalW {
			modalW = w
		}
	}
	if modalW > h.width-4 && h.width > 8 {
		modalW = h.width - 4
	}

	return lipgloss.NewStyle().
		Border(lipgloss.RoundedBorder()).
		BorderForeground(ColorSecondary).
		Width(modalW).
		Padding(0, 1).
		Render(content)
}

func fmtVal(v float64, typ string) string {
	if typ == "float" {
		return fmt.Sprintf("%.1f", v)
	}
	return fmt.Sprintf("%.4g", v)
}
