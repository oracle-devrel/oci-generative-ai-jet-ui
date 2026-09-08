package ui

import (
	"fmt"
	"strings"

	"github.com/charmbracelet/lipgloss"
)

// ModelSelector represents the model selection popup
type ModelSelector struct {
	models   []string
	selected int
	active   bool
	width    int
	height   int
	loading  bool
	error    string
}

// NewModelSelector creates a new model selector
func NewModelSelector() *ModelSelector {
	return &ModelSelector{
		models:   []string{},
		selected: 0,
		active:   false,
		width:    40,
		height:   15,
		loading:  false,
		error:    "",
	}
}

// SetModels updates the available models
func (m *ModelSelector) SetModels(models []string) {
	m.models = models
	m.selected = 0
	m.loading = false
	m.error = ""
}

// SetLoading sets the loading state
func (m *ModelSelector) SetLoading(loading bool) {
	m.loading = loading
}

// SetError sets an error message
func (m *ModelSelector) SetError(err string) {
	m.error = err
	m.loading = false
}

// Show activates the model selector
func (m *ModelSelector) Show() {
	m.active = true
}

// Hide deactivates the model selector
func (m *ModelSelector) Hide() {
	m.active = false
}

// IsActive returns whether the selector is active
func (m *ModelSelector) IsActive() bool {
	return m.active
}

// MoveUp moves selection up
func (m *ModelSelector) MoveUp() {
	if len(m.models) == 0 {
		return
	}
	m.selected--
	if m.selected < 0 {
		m.selected = len(m.models) - 1
	}
}

// MoveDown moves selection down
func (m *ModelSelector) MoveDown() {
	if len(m.models) == 0 {
		return
	}
	m.selected++
	if m.selected >= len(m.models) {
		m.selected = 0
	}
}

// Selected returns the currently selected model
func (m *ModelSelector) Selected() string {
	if m.selected >= 0 && m.selected < len(m.models) {
		return m.models[m.selected]
	}
	return ""
}

// SetSize updates the selector dimensions
func (m *ModelSelector) SetSize(width, height int) {
	m.width = width
	m.height = height
}

// View renders the model selector
func (m *ModelSelector) View() string {
	if !m.active {
		return ""
	}

	var b strings.Builder

	title := lipgloss.NewStyle().Bold(true).Foreground(ColorPrimary).Render("Select Model")
	b.WriteString(title)
	b.WriteString("\n")
	b.WriteString(strings.Repeat("─", m.width-4))
	b.WriteString("\n\n")

	if m.loading {
		b.WriteString(ChatStreamingStyle.Render("Loading models..."))
	} else if m.error != "" {
		b.WriteString(lipgloss.NewStyle().Foreground(ColorError).Render(m.error))
	} else if len(m.models) == 0 {
		b.WriteString(lipgloss.NewStyle().Foreground(ColorWarning).Render("No models found"))
	} else {
		for i, model := range m.models {
			var prefix string
			var style lipgloss.Style

			if i == m.selected {
				prefix = "● "
				style = SidebarSelectedStyle
			} else {
				prefix = "○ "
				style = SidebarItemStyle
			}

			line := style.Render(fmt.Sprintf("%s%s", prefix, model))
			b.WriteString(line)
			b.WriteString("\n")
		}
	}

	b.WriteString("\n")
	b.WriteString(HelpStyle.Render("↑/↓: navigate  Enter: select  Esc: cancel"))

	boxStyle := lipgloss.NewStyle().
		Border(lipgloss.RoundedBorder()).
		BorderForeground(ColorPrimary).
		Padding(1, 2).
		Width(m.width).
		Height(m.height)

	return boxStyle.Render(b.String())
}
