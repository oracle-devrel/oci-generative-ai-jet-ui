package ui

import (
	"fmt"
	"strings"

	"github.com/charmbracelet/lipgloss"
)

// Agent represents a reasoning strategy
type Agent struct {
	ID          string
	Name        string
	Description string
}

// DefaultAgents returns the list of available agents
func DefaultAgents() []Agent {
	return []Agent{
		{ID: "standard", Name: "Standard", Description: "Direct generation"},
		{ID: "cot", Name: "CoT", Description: "Chain of Thought"},
		{ID: "tot", Name: "ToT", Description: "Tree of Thoughts"},
		{ID: "react", Name: "ReAct", Description: "Reason + Act"},
		{ID: "recursive", Name: "Recursive", Description: "Recursive LM"},
		{ID: "reflection", Name: "Reflection", Description: "Self-Reflection"},
		{ID: "refinement", Name: "Refinement", Description: "Score-based refinement"},
		{ID: "complex_refinement", Name: "Pipeline", Description: "5-stage optimization"},
		{ID: "decomposed", Name: "Decomposed", Description: "Problem decomposition"},
		{ID: "least_to_most", Name: "Least-to-Most", Description: "Incremental solving"},
		{ID: "consistency", Name: "Consistency", Description: "Self-Consistency"},
	}
}

// SidebarItem represents an item in the sidebar
type SidebarItem struct {
	Label    string
	Value    string
	IsAgent  bool
	IsSeparator bool
}

// Sidebar represents the left panel with agent selection
type Sidebar struct {
	items    []SidebarItem
	selected int
	height   int
	focused  bool
}

// AgentItem is a minimal struct used to populate the sidebar dynamically,
// avoiding circular imports with the app package.
type AgentItem struct {
	ID   string
	Name string
}

// buildSidebarItems constructs the full item list from an agent slice.
func buildSidebarItems(agents []AgentItem) []SidebarItem {
	items := []SidebarItem{}

	for _, a := range agents {
		items = append(items, SidebarItem{
			Label:   a.Name,
			Value:   a.ID,
			IsAgent: true,
		})
	}

	// Action items
	items = append(items, SidebarItem{IsSeparator: true})
	items = append(items, SidebarItem{Label: "Arena Mode", Value: "arena"})
	items = append(items, SidebarItem{Label: "Head-to-Head", Value: "duel"})
	items = append(items, SidebarItem{Label: "Debugger", Value: "debug"})
	items = append(items, SidebarItem{Label: "Benchmarks", Value: "benchmark"})
	items = append(items, SidebarItem{Label: "Sessions", Value: "sessions"})
	items = append(items, SidebarItem{Label: "Agent Guide", Value: "agent_info"})
	items = append(items, SidebarItem{IsSeparator: true})
	items = append(items, SidebarItem{Label: "Select Model", Value: "model"})

	return items
}

// NewSidebar creates a new sidebar component using the default hardcoded agents.
func NewSidebar() *Sidebar {
	agents := []AgentItem{}
	for _, a := range DefaultAgents() {
		agents = append(agents, AgentItem{ID: a.ID, Name: a.Name})
	}
	return &Sidebar{
		items:    buildSidebarItems(agents),
		selected: 0,
		height:   20,
		focused:  true,
	}
}

// NewSidebarFromAgents creates a sidebar from a dynamic agent list fetched from the server.
func NewSidebarFromAgents(agents []AgentItem) *Sidebar {
	return &Sidebar{
		items:    buildSidebarItems(agents),
		selected: 0,
		height:   20,
		focused:  true,
	}
}

// SetHeight updates the sidebar height
func (s *Sidebar) SetHeight(height int) {
	s.height = height
}

// SetFocused updates the focus state
func (s *Sidebar) SetFocused(focused bool) {
	s.focused = focused
}

// IsFocused returns whether the sidebar is focused
func (s *Sidebar) IsFocused() bool {
	return s.focused
}

// MoveUp moves selection up
func (s *Sidebar) MoveUp() {
	for {
		s.selected--
		if s.selected < 0 {
			s.selected = len(s.items) - 1
		}
		if !s.items[s.selected].IsSeparator {
			break
		}
	}
}

// MoveDown moves selection down
func (s *Sidebar) MoveDown() {
	for {
		s.selected++
		if s.selected >= len(s.items) {
			s.selected = 0
		}
		if !s.items[s.selected].IsSeparator {
			break
		}
	}
}

// Selected returns the currently selected item value
func (s *Sidebar) Selected() string {
	if s.selected >= 0 && s.selected < len(s.items) {
		return s.items[s.selected].Value
	}
	return ""
}

// SelectedItem returns the currently selected item
func (s *Sidebar) SelectedItem() SidebarItem {
	if s.selected >= 0 && s.selected < len(s.items) {
		return s.items[s.selected]
	}
	return SidebarItem{}
}

// View renders the sidebar
func (s *Sidebar) View() string {
	var b strings.Builder

	title := SidebarTitleStyle.Render("AGENTS")
	b.WriteString(title)
	b.WriteString("\n")

	for i, item := range s.items {
		if item.IsSeparator {
			b.WriteString(SidebarSeparatorStyle.Render("─────────────────"))
			b.WriteString("\n")
			continue
		}

		var prefix string
		var style lipgloss.Style

		if i == s.selected && s.focused {
			prefix = "● "
			style = SidebarSelectedStyle
		} else {
			prefix = "○ "
			style = SidebarItemStyle
		}

		// Special styling for non-agent items
		if !item.IsAgent && item.Value == "arena" {
			prefix = "⚔ "
		} else if !item.IsAgent && item.Value == "benchmark" {
			prefix = "📊 "
		} else if !item.IsAgent && item.Value == "model" {
			prefix = "⚙ "
		}

		line := style.Render(fmt.Sprintf("%s%s", prefix, item.Label))
		b.WriteString(line)
		b.WriteString("\n")
	}

	return SidebarStyle.Height(s.height).Render(b.String())
}
