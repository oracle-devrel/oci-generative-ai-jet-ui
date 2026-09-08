package ui

import (
	"fmt"

	"github.com/charmbracelet/lipgloss"
)

// Header represents the top status bar
type Header struct {
	title     string
	model     string
	connected bool
	width     int
}

// NewHeader creates a new header component
func NewHeader() *Header {
	return &Header{
		title:     "Agent Reasoning TUI",
		model:     "gemma3:latest",
		connected: false,
		width:     80,
	}
}

// SetModel updates the current model
func (h *Header) SetModel(model string) {
	h.model = model
}

// SetConnected updates the connection status
func (h *Header) SetConnected(connected bool) {
	h.connected = connected
}

// SetWidth updates the header width
func (h *Header) SetWidth(width int) {
	h.width = width
}

// View renders the header
func (h *Header) View() string {
	title := HeaderTitleStyle.Render(h.title)
	model := HeaderModelStyle.Render(fmt.Sprintf("Model: %s", h.model))

	var status string
	if h.connected {
		status = HeaderConnectedStyle.Render("● Connected")
	} else {
		status = HeaderDisconnectedStyle.Render("○ Disconnected")
	}

	// Calculate spacing
	leftPart := title
	rightPart := fmt.Sprintf("%s    %s", model, status)

	leftWidth := lipgloss.Width(leftPart)
	rightWidth := lipgloss.Width(rightPart)
	spacing := h.width - leftWidth - rightWidth - 4 // Account for padding

	if spacing < 1 {
		spacing = 1
	}

	spacer := lipgloss.NewStyle().Width(spacing).Render("")

	content := lipgloss.JoinHorizontal(lipgloss.Top, leftPart, spacer, rightPart)

	return HeaderStyle.Width(h.width).Render(content)
}
