package ui

import (
	"fmt"
	"strings"
	"sync"

	"github.com/charmbracelet/lipgloss"
)

// ArenaStatus represents the status of an agent in arena mode
type ArenaStatus int

const (
	ArenaWaiting ArenaStatus = iota
	ArenaRunning
	ArenaDone
	ArenaError
)

// ArenaCell represents a single cell in the arena grid
type ArenaCell struct {
	AgentID   string
	AgentName string
	Status    ArenaStatus
	Content   string
	Duration  float64
	Error     string
}

// Arena represents the arena grid view
type Arena struct {
	mu         sync.Mutex
	cells      []*ArenaCell
	query      string
	width      int
	height     int
	active     bool
	completed  int
}

// NewArena creates a new arena component
func NewArena() *Arena {
	agents := DefaultAgents()
	cells := make([]*ArenaCell, len(agents))

	for i, agent := range agents {
		cells[i] = &ArenaCell{
			AgentID:   agent.ID,
			AgentName: agent.Name,
			Status:    ArenaWaiting,
			Content:   "",
		}
	}

	return &Arena{
		cells:     cells,
		query:     "",
		width:     80,
		height:    40,
		active:    false,
		completed: 0,
	}
}

// SetSize updates the arena dimensions
func (a *Arena) SetSize(width, height int) {
	a.mu.Lock()
	defer a.mu.Unlock()
	a.width = width
	a.height = height
}

// Start begins the arena run with a query
func (a *Arena) Start(query string) {
	a.mu.Lock()
	defer a.mu.Unlock()
	a.query = query
	a.active = true
	a.completed = 0

	// Reset all cells
	for _, cell := range a.cells {
		cell.Status = ArenaWaiting
		cell.Content = ""
		cell.Duration = 0
		cell.Error = ""
	}
}

// Stop ends the arena mode
func (a *Arena) Stop() {
	a.mu.Lock()
	defer a.mu.Unlock()
	a.active = false
}

// IsActive returns whether arena mode is active
func (a *Arena) IsActive() bool {
	a.mu.Lock()
	defer a.mu.Unlock()
	return a.active
}

// GetCells returns all cells
func (a *Arena) GetCells() []*ArenaCell {
	a.mu.Lock()
	defer a.mu.Unlock()
	return a.cells
}

// getCell returns a cell by agent ID (caller must hold a.mu).
func (a *Arena) getCell(agentID string) *ArenaCell {
	for _, cell := range a.cells {
		if cell.AgentID == agentID {
			return cell
		}
	}
	return nil
}

// GetCell returns a cell by agent ID
func (a *Arena) GetCell(agentID string) *ArenaCell {
	a.mu.Lock()
	defer a.mu.Unlock()
	return a.getCell(agentID)
}

// SetCellStatus updates a cell's status
func (a *Arena) SetCellStatus(agentID string, status ArenaStatus) {
	a.mu.Lock()
	defer a.mu.Unlock()
	if cell := a.getCell(agentID); cell != nil {
		cell.Status = status
		if status == ArenaDone || status == ArenaError {
			a.completed++
		}
	}
}

// SetCellContent updates a cell's content
func (a *Arena) SetCellContent(agentID, content string) {
	a.mu.Lock()
	defer a.mu.Unlock()
	if cell := a.getCell(agentID); cell != nil {
		cell.Content = content
	}
}

// AppendCellContent appends to a cell's content
func (a *Arena) AppendCellContent(agentID, content string) {
	a.mu.Lock()
	defer a.mu.Unlock()
	if cell := a.getCell(agentID); cell != nil {
		cell.Content += content
	}
}

// SetCellDuration sets the duration for a cell
func (a *Arena) SetCellDuration(agentID string, duration float64) {
	a.mu.Lock()
	defer a.mu.Unlock()
	if cell := a.getCell(agentID); cell != nil {
		cell.Duration = duration
	}
}

// SetCellError sets an error for a cell
func (a *Arena) SetCellError(agentID, err string) {
	a.mu.Lock()
	defer a.mu.Unlock()
	if cell := a.getCell(agentID); cell != nil {
		cell.Error = err
		cell.Status = ArenaError
	}
}

// IsComplete returns whether all agents have finished
func (a *Arena) IsComplete() bool {
	a.mu.Lock()
	defer a.mu.Unlock()
	return a.completed >= len(a.cells)
}

// Query returns the current query
func (a *Arena) Query() string {
	a.mu.Lock()
	defer a.mu.Unlock()
	return a.query
}

// View renders the arena grid
func (a *Arena) View() string {
	a.mu.Lock()
	defer a.mu.Unlock()

	if !a.active {
		return ""
	}

	// Calculate cell dimensions (3x3 grid)
	cellWidth := (a.width - 4) / 3
	cellHeight := (a.height - 6) / 3

	// Render header
	queryDisplay := a.query
	if len(queryDisplay) > 40 {
		queryDisplay = queryDisplay[:37] + "..."
	}
	header := ArenaHeaderStyle.Render(fmt.Sprintf("⚔ ARENA MODE    Query: \"%s\"    [Esc to exit]", queryDisplay))

	// Render grid
	var rows []string

	for row := 0; row < 3; row++ {
		var rowCells []string

		for col := 0; col < 3; col++ {
			idx := row*3 + col
			if idx < len(a.cells) {
				cell := a.cells[idx]
				rendered := a.renderCell(cell, cellWidth, cellHeight)
				rowCells = append(rowCells, rendered)
			}
		}

		rowStr := lipgloss.JoinHorizontal(lipgloss.Top, rowCells...)
		rows = append(rows, rowStr)
	}

	grid := lipgloss.JoinVertical(lipgloss.Left, rows...)

	// Combine header and grid
	return lipgloss.JoinVertical(lipgloss.Left, header, "", grid)
}

// renderCell renders a single arena cell
func (a *Arena) renderCell(cell *ArenaCell, width, height int) string {
	// Status indicator and title
	var statusStr string
	var style lipgloss.Style

	switch cell.Status {
	case ArenaWaiting:
		statusStr = ArenaStatusWaiting.Render("○ waiting")
		style = ArenaCellStyle
	case ArenaRunning:
		statusStr = ArenaStatusRunning.Render("● streaming...")
		style = ArenaCellActiveStyle
	case ArenaDone:
		statusStr = ArenaStatusDone.Render(fmt.Sprintf("✓ %.1fs", cell.Duration))
		style = ArenaCellDoneStyle
	case ArenaError:
		statusStr = lipgloss.NewStyle().Foreground(ColorError).Render("✗ error")
		style = ArenaCellStyle
	}

	title := lipgloss.NewStyle().Bold(true).Render(cell.AgentName)
	header := fmt.Sprintf("%s %s", title, statusStr)

	// Content (truncate if needed)
	content := cell.Content
	if cell.Error != "" {
		content = cell.Error
	}

	// Truncate content to fit
	maxContentLines := height - 3
	lines := strings.Split(content, "\n")
	if len(lines) > maxContentLines {
		lines = lines[:maxContentLines]
		lines[len(lines)-1] = "..."
	}

	// Truncate line length
	maxLineLen := width - 4
	for i, line := range lines {
		if len(line) > maxLineLen {
			lines[i] = line[:maxLineLen-3] + "..."
		}
	}

	contentStr := strings.Join(lines, "\n")

	fullContent := lipgloss.JoinVertical(lipgloss.Left, header, contentStr)

	return style.Width(width).Height(height).Render(fullContent)
}

// RenderSummary renders a summary table after arena completion
func (a *Arena) RenderSummary() string {
	a.mu.Lock()
	defer a.mu.Unlock()

	var b strings.Builder

	b.WriteString(ArenaHeaderStyle.Render("Arena Results Summary"))
	b.WriteString("\n\n")

	// Table header
	headerStyle := lipgloss.NewStyle().Bold(true).Foreground(ColorPrimary)
	b.WriteString(headerStyle.Render(fmt.Sprintf("%-15s %-10s %-10s", "Agent", "Time", "Length")))
	b.WriteString("\n")
	b.WriteString(strings.Repeat("─", 40))
	b.WriteString("\n")

	// Table rows
	for _, cell := range a.cells {
		var timeStr string
		if cell.Status == ArenaDone {
			timeStr = fmt.Sprintf("%.2fs", cell.Duration)
		} else if cell.Status == ArenaError {
			timeStr = "error"
		} else {
			timeStr = "-"
		}

		lenStr := fmt.Sprintf("%d", len(cell.Content))

		b.WriteString(fmt.Sprintf("%-15s %-10s %-10s\n", cell.AgentName, timeStr, lenStr))
	}

	return b.String()
}
