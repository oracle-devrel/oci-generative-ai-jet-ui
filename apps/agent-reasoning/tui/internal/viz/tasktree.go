package viz

import (
	"fmt"
	"strings"

	"agent-reasoning-tui/internal/client"
	"agent-reasoning-tui/internal/ui"

	"github.com/charmbracelet/lipgloss"
)

var (
	taskPendingStyle   = lipgloss.NewStyle().Foreground(lipgloss.Color("#888888"))
	taskRunningStyle   = lipgloss.NewStyle().Foreground(lipgloss.Color("#FFFF00"))
	taskCompletedStyle = lipgloss.NewStyle().Foreground(lipgloss.Color("#00FF00"))
	taskFailedStyle    = lipgloss.NewStyle().Foreground(lipgloss.Color("#FF0000"))
)

type taskEntry struct {
	id          string
	description string
	status      string
	result      string
}

// TaskTreeViz renders Decomposed/LTM task events with a progress bar and status icons.
type TaskTreeViz struct {
	tasks         []taskEntry
	progress      *ui.ProgressBar
	width, height int
}

func NewTaskTreeViz(width, height int) Visualizer {
	return &TaskTreeViz{
		width:  width,
		height: height,
	}
}

func (v *TaskTreeViz) Reset() {
	v.tasks = nil
	v.progress = nil
}

func (v *TaskTreeViz) SetSize(width, height int) {
	v.width = width
	v.height = height
	v.rebuildProgress()
}

func (v *TaskTreeViz) Update(event client.StructuredEvent) {
	switch event.EventType {
	case "task":
		id := getString(event.Data, "id")
		desc := getString(event.Data, "description")
		status := getString(event.Data, "status")
		result := getString(event.Data, "result")

		// Update existing task or add new one
		found := false
		for i, t := range v.tasks {
			if t.id == id {
				if status != "" {
					v.tasks[i].status = status
				}
				if result != "" {
					v.tasks[i].result = result
				}
				found = true
				break
			}
		}
		if !found {
			v.tasks = append(v.tasks, taskEntry{
				id: id, description: desc, status: status, result: result,
			})
		}
		v.rebuildProgress()

	case "final":
		// Mark all running tasks as completed
		for i, t := range v.tasks {
			if t.status == "running" {
				v.tasks[i].status = "completed"
			}
		}
		v.rebuildProgress()
	}
}

func (v *TaskTreeViz) rebuildProgress() {
	if len(v.tasks) == 0 {
		return
	}
	// Build stage names from task descriptions (truncated)
	names := make([]string, len(v.tasks))
	completedCount := 0
	for i, t := range v.tasks {
		names[i] = truncateStr(t.description, 12)
		if t.status == "completed" {
			completedCount++
		}
	}
	v.progress = ui.NewProgressBar(names, v.width)
	if completedCount > 0 {
		v.progress.SetCurrent(completedCount - 1)
	}
}

func (v *TaskTreeViz) View() string {
	if len(v.tasks) == 0 {
		return taskPendingStyle.Render("Waiting for tasks...")
	}

	var lines []string

	// Progress bar at top
	if v.progress != nil {
		lines = append(lines, v.progress.View())
		lines = append(lines, strings.Repeat("─", v.width))
	}

	// Task list with status icons
	for _, t := range v.tasks {
		icon, styled := taskIcon(t.status, t.description)
		line := icon + " " + styled
		if t.result != "" {
			line += fmt.Sprintf(" → %s", truncateStr(t.result, v.width-len(t.description)-10))
		}
		lines = append(lines, line)
	}

	return strings.Join(lines, "\n")
}

func taskIcon(status, description string) (string, string) {
	switch status {
	case "pending":
		return taskPendingStyle.Render("[ ]"), taskPendingStyle.Render(description)
	case "running":
		return taskRunningStyle.Render("[●]"), taskRunningStyle.Render(description)
	case "completed":
		return taskCompletedStyle.Render("[✓]"), taskCompletedStyle.Render(description)
	case "failed":
		return taskFailedStyle.Render("[✗]"), taskFailedStyle.Render(description)
	default:
		return taskPendingStyle.Render("[ ]"), taskPendingStyle.Render(description)
	}
}
