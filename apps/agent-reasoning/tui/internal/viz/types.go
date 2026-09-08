package viz

import "agent-reasoning-tui/internal/client"

// Visualizer processes structured events and renders terminal output.
type Visualizer interface {
	Update(event client.StructuredEvent)
	View() string
	SetSize(width, height int)
	Reset()
}
