package ui

import (
	"strings"

	"github.com/charmbracelet/lipgloss"
)

// LaneConfig defines a swimlane's name and color.
type LaneConfig struct {
	Name  string
	Color string
}

// LaneRow is a single content entry in a specific lane.
type LaneRow struct {
	Lane    int
	Content string
}

// Swimlane renders N parallel vertical tracks.
type Swimlane struct {
	lanes         []LaneConfig
	rows          []LaneRow
	width, height int
}

func NewSwimlane(width, height int, lanes []LaneConfig) *Swimlane {
	return &Swimlane{
		lanes:  lanes,
		width:  width,
		height: height,
	}
}

// AddRow adds content to the specified lane index.
func (s *Swimlane) AddRow(lane int, content string) {
	if lane < 0 || lane >= len(s.lanes) {
		return
	}
	s.rows = append(s.rows, LaneRow{Lane: lane, Content: content})
}

// View renders the swimlane with headers separated by │ and rows with active lane content.
func (s *Swimlane) View() string {
	if len(s.lanes) == 0 {
		return ""
	}

	// Lane width: split evenly
	laneWidth := (s.width - (len(s.lanes) - 1)) / len(s.lanes)
	if laneWidth < 1 {
		laneWidth = 1
	}

	// Build header
	headerCells := make([]string, len(s.lanes))
	for i, lane := range s.lanes {
		st := lipgloss.NewStyle().
			Foreground(lipgloss.Color(lane.Color)).
			Bold(true).
			Width(laneWidth)
		headerCells[i] = st.Render(truncateStr(lane.Name, laneWidth))
	}
	header := strings.Join(headerCells, "│")

	// Separator line
	sepParts := make([]string, len(s.lanes))
	for i := range s.lanes {
		sepParts[i] = strings.Repeat("─", laneWidth)
	}
	separator := strings.Join(sepParts, "┼")

	var lines []string
	lines = append(lines, header)
	lines = append(lines, separator)

	// Render rows — limit to height
	maxRows := s.height - 2
	if maxRows < 0 {
		maxRows = 0
	}

	for idx, row := range s.rows {
		if idx >= maxRows {
			break
		}
		cells := make([]string, len(s.lanes))
		for i, lane := range s.lanes {
			st := lipgloss.NewStyle().
				Foreground(lipgloss.Color(lane.Color)).
				Width(laneWidth)
			if i == row.Lane {
				cells[i] = st.Render(truncateStr(row.Content, laneWidth))
			} else {
				cells[i] = st.Render("")
			}
		}
		lines = append(lines, strings.Join(cells, "│"))
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
