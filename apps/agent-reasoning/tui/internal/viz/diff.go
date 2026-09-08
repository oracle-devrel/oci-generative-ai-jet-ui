package viz

import (
	"agent-reasoning-tui/internal/client"
	"agent-reasoning-tui/internal/ui"
)

// DiffViz renders Reflection/Refinement iteration events.
type DiffViz struct {
	view          *ui.DiffView
	width, height int
}

func NewDiffViz(width, height int) Visualizer {
	return &DiffViz{
		view:   ui.NewDiffView(width, height),
		width:  width,
		height: height,
	}
}

func (v *DiffViz) Reset() {
	v.view = ui.NewDiffView(v.width, v.height)
}

func (v *DiffViz) SetSize(width, height int) {
	v.width = width
	v.height = height
	v.view = ui.NewDiffView(width, height)
}

func (v *DiffViz) Update(event client.StructuredEvent) {
	switch event.EventType {
	case "iteration", "refinement":
		content := getString(event.Data, "content")
		score := getFloat(event.Data, "score")
		critique := getString(event.Data, "critique")
		if critique != "" {
			content = content + "\n[Critique: " + critique + "]"
		}
		v.view.AddIteration(content, score)

	case "final":
		content := getString(event.Data, "content")
		if content != "" {
			v.view.AddIteration(content, 1.0)
		}
	}
}

func (v *DiffViz) View() string {
	result := v.view.View()
	if result == "" {
		return "Waiting for iterations..."
	}
	return result
}
