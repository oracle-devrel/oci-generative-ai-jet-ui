package ui

import (
	"github.com/charmbracelet/lipgloss"
)

// Splash screen styles
var (
	splashBannerStyle = lipgloss.NewStyle().
				Foreground(lipgloss.Color("#5E5CE6")).
				Bold(true)

	splashTitleStyle = lipgloss.NewStyle().
				Foreground(ColorPrimary).
				Bold(true)

	splashSubtitleStyle = lipgloss.NewStyle().
				Foreground(ColorMuted).
				Italic(true)

	splashHintStyle = lipgloss.NewStyle().
			Foreground(ColorMuted)
)

// RenderSplash generates the block-letter splash screen centered in the given dimensions.
func RenderSplash(width, height int) string {
	subtitle := splashSubtitleStyle.Render("From tokens to thoughts")

	// Fallback for very small terminals
	if width < 40 || height < 16 {
		title := splashTitleStyle.Render("AGENT REASONING")
		small := lipgloss.JoinVertical(lipgloss.Center, title, subtitle)
		return lipgloss.Place(width, height, lipgloss.Center, lipgloss.Center, small)
	}

	art := buildBlockBanner()
	hint := splashHintStyle.Render("Tab focus  |  Enter send  |  q quit")

	content := lipgloss.JoinVertical(lipgloss.Center,
		art,
		"",
		subtitle,
		"",
		hint,
	)

	return lipgloss.Place(width, height, lipgloss.Center, lipgloss.Center, content)
}

func buildBlockBanner() string {
	b := func(t string) string { return splashBannerStyle.Render(t) }

	lines := []string{
		b("  █████╗  ██████╗ ███████╗███╗   ██╗████████╗"),
		b(" ██╔══██╗██╔════╝ ██╔════╝████╗  ██║╚══██╔══╝"),
		b(" ███████║██║  ███╗█████╗  ██╔██╗ ██║   ██║   "),
		b(" ██╔══██║██║   ██║██╔══╝  ██║╚██╗██║   ██║   "),
		b(" ██║  ██║╚██████╔╝███████╗██║ ╚████║   ██║   "),
		b(" ╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚═╝  ╚═══╝   ╚═╝   "),
		b(" ██████╗ ███████╗ █████╗ ███████╗ ██████╗ ███╗   ██╗██╗███╗   ██╗ ██████╗ "),
		b(" ██╔══██╗██╔════╝██╔══██╗██╔════╝██╔═══██╗████╗  ██║██║████╗  ██║██╔════╝ "),
		b(" ██████╔╝█████╗  ███████║███████╗██║   ██║██╔██╗ ██║██║██╔██╗ ██║██║  ███╗"),
		b(" ██╔══██╗██╔══╝  ██╔══██║╚════██║██║   ██║██║╚██╗██║██║██║╚██╗██║██║   ██║"),
		b(" ██║  ██║███████╗██║  ██║███████║╚██████╔╝██║ ╚████║██║██║ ╚████║╚██████╔╝"),
		b(" ╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝╚══════╝ ╚═════╝ ╚═╝  ╚═══╝╚═╝╚═╝  ╚═══╝ ╚═════╝ "),
	}

	return lipgloss.JoinVertical(lipgloss.Left, lines...)
}
