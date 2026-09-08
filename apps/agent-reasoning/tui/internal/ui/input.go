package ui

import (
	"github.com/charmbracelet/bubbles/textinput"
	tea "github.com/charmbracelet/bubbletea"
)

// Input represents the text input component
type Input struct {
	textInput textinput.Model
	width     int
	focused   bool
}

// NewInput creates a new input component
func NewInput() *Input {
	ti := textinput.New()
	ti.Placeholder = "Enter your query..."
	ti.CharLimit = 1000
	ti.Width = 60

	return &Input{
		textInput: ti,
		width:     80,
		focused:   false,
	}
}

// SetWidth updates the input width
func (i *Input) SetWidth(width int) {
	i.width = width
	i.textInput.Width = width - 6 // Account for prompt and padding
}

// Focus focuses the input
func (i *Input) Focus() {
	i.focused = true
	i.textInput.Focus()
}

// Blur unfocuses the input
func (i *Input) Blur() {
	i.focused = false
	i.textInput.Blur()
}

// IsFocused returns whether the input is focused
func (i *Input) IsFocused() bool {
	return i.focused
}

// Value returns the current input value
func (i *Input) Value() string {
	return i.textInput.Value()
}

// SetValue sets the input value
func (i *Input) SetValue(value string) {
	i.textInput.SetValue(value)
}

// Reset clears the input
func (i *Input) Reset() {
	i.textInput.Reset()
}

// SetPlaceholder updates the placeholder text.
func (i *Input) SetPlaceholder(text string) {
	i.textInput.Placeholder = text
}

// Update handles input updates
func (i *Input) Update(msg tea.Msg) (*Input, tea.Cmd) {
	var cmd tea.Cmd
	i.textInput, cmd = i.textInput.Update(msg)
	return i, cmd
}

// View renders the input
func (i *Input) View() string {
	prompt := InputPromptStyle.Render("> ")

	var style = InputStyle
	if i.focused {
		style = InputFocusedStyle
	}

	return style.Width(i.width).Render(prompt + i.textInput.View())
}
