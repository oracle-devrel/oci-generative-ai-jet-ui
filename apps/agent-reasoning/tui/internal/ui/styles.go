package ui

import (
	"github.com/charmbracelet/lipgloss"
)

var (
	// Colors
	ColorPrimary   = lipgloss.Color("#00FFFF") // Cyan
	ColorSecondary = lipgloss.Color("#FF00FF") // Magenta
	ColorSuccess   = lipgloss.Color("#00FF00") // Green
	ColorWarning   = lipgloss.Color("#FFFF00") // Yellow
	ColorError     = lipgloss.Color("#FF0000") // Red
	ColorMuted     = lipgloss.Color("#666666") // Gray
	ColorWhite     = lipgloss.Color("#FFFFFF")
	ColorBlack     = lipgloss.Color("#000000")

	// Sidebar styles
	SidebarWidth = 20

	SidebarStyle = lipgloss.NewStyle().
			Width(SidebarWidth).
			BorderStyle(lipgloss.NormalBorder()).
			BorderRight(true).
			BorderForeground(ColorMuted).
			Padding(1, 1)

	SidebarTitleStyle = lipgloss.NewStyle().
				Bold(true).
				Foreground(ColorPrimary).
				MarginBottom(1)

	SidebarItemStyle = lipgloss.NewStyle().
				Foreground(ColorWhite)

	SidebarSelectedStyle = lipgloss.NewStyle().
				Foreground(ColorPrimary).
				Bold(true)

	SidebarSeparatorStyle = lipgloss.NewStyle().
				Foreground(ColorMuted)

	// Header styles
	HeaderStyle = lipgloss.NewStyle().
			BorderStyle(lipgloss.NormalBorder()).
			BorderBottom(true).
			BorderForeground(ColorMuted).
			Padding(0, 1)

	HeaderTitleStyle = lipgloss.NewStyle().
				Bold(true).
				Foreground(ColorPrimary)

	HeaderModelStyle = lipgloss.NewStyle().
				Foreground(ColorWarning)

	HeaderConnectedStyle = lipgloss.NewStyle().
				Foreground(ColorSuccess)

	HeaderDisconnectedStyle = lipgloss.NewStyle().
				Foreground(ColorError)

	// Chat panel styles
	ChatPanelStyle = lipgloss.NewStyle().
			Padding(1, 2)

	ChatTitleStyle = lipgloss.NewStyle().
			Bold(true).
			Foreground(ColorSecondary).
			MarginBottom(1)

	ChatUserStyle = lipgloss.NewStyle().
			Bold(true).
			Foreground(ColorSuccess)

	ChatAssistantStyle = lipgloss.NewStyle().
				Foreground(ColorWhite)

	ChatStreamingStyle = lipgloss.NewStyle().
				Foreground(ColorMuted).
				Italic(true)

	// Input styles
	InputStyle = lipgloss.NewStyle().
			BorderStyle(lipgloss.NormalBorder()).
			BorderTop(true).
			BorderForeground(ColorMuted).
			Padding(0, 1)

	InputPromptStyle = lipgloss.NewStyle().
				Foreground(ColorSuccess).
				Bold(true)

	InputTextStyle = lipgloss.NewStyle().
			Foreground(ColorWhite)

	InputFocusedStyle = lipgloss.NewStyle().
				BorderStyle(lipgloss.NormalBorder()).
				BorderTop(true).
				BorderForeground(ColorPrimary).
				Padding(0, 1)

	// Arena styles
	ArenaCellStyle = lipgloss.NewStyle().
			BorderStyle(lipgloss.NormalBorder()).
			BorderForeground(ColorMuted).
			Padding(0, 1)

	ArenaCellActiveStyle = lipgloss.NewStyle().
				BorderStyle(lipgloss.NormalBorder()).
				BorderForeground(ColorPrimary).
				Padding(0, 1)

	ArenaCellDoneStyle = lipgloss.NewStyle().
				BorderStyle(lipgloss.NormalBorder()).
				BorderForeground(ColorSuccess).
				Padding(0, 1)

	ArenaHeaderStyle = lipgloss.NewStyle().
				Bold(true).
				Foreground(ColorWarning)

	ArenaStatusWaiting = lipgloss.NewStyle().
				Foreground(ColorMuted)

	ArenaStatusRunning = lipgloss.NewStyle().
				Foreground(ColorPrimary)

	ArenaStatusDone = lipgloss.NewStyle().
			Foreground(ColorSuccess)

	// Help style
	HelpStyle = lipgloss.NewStyle().
			Foreground(ColorMuted).
			Italic(true)
)

// Helper function to create a box with title
func BoxWithTitle(title, content string, width int, style lipgloss.Style) string {
	titleRendered := lipgloss.NewStyle().Bold(true).Foreground(ColorPrimary).Render(title)
	return style.Width(width).Render(titleRendered + "\n" + content)
}
