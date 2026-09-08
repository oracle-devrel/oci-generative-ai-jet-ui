package viz

import (
	"fmt"

	"agent-reasoning-tui/internal/client"
	"agent-reasoning-tui/internal/ui"
)

// SwimlaneViz renders ReAct react_step events as a 3-lane swimlane.
type SwimlaneViz struct {
	lane          *ui.Swimlane
	width, height int
}

func NewSwimlaneViz(width, height int) Visualizer {
	lanes := []ui.LaneConfig{
		{Name: "Thought", Color: "#00FFFF"},
		{Name: "Action", Color: "#FFFF00"},
		{Name: "Observation", Color: "#00FF00"},
	}
	return &SwimlaneViz{
		lane:   ui.NewSwimlane(width, height, lanes),
		width:  width,
		height: height,
	}
}

func (v *SwimlaneViz) Reset() {
	lanes := []ui.LaneConfig{
		{Name: "Thought", Color: "#00FFFF"},
		{Name: "Action", Color: "#FFFF00"},
		{Name: "Observation", Color: "#00FF00"},
	}
	v.lane = ui.NewSwimlane(v.width, v.height, lanes)
}

func (v *SwimlaneViz) SetSize(width, height int) {
	v.width = width
	v.height = height
	lanes := []ui.LaneConfig{
		{Name: "Thought", Color: "#00FFFF"},
		{Name: "Action", Color: "#FFFF00"},
		{Name: "Observation", Color: "#00FF00"},
	}
	v.lane = ui.NewSwimlane(width, height, lanes)
}

func (v *SwimlaneViz) Update(event client.StructuredEvent) {
	switch event.EventType {
	case "react_step":
		step := getInt(event.Data, "step")
		prefix := fmt.Sprintf("[%d] ", step)

		thought := getString(event.Data, "thought")
		action := getString(event.Data, "action")
		observation := getString(event.Data, "observation")

		if thought != "" {
			v.lane.AddRow(0, prefix+thought)
		}
		if action != "" {
			v.lane.AddRow(1, prefix+action)
		}
		if observation != "" {
			v.lane.AddRow(2, prefix+observation)
		}

	case "final":
		answer := getString(event.Data, "content")
		if answer == "" {
			answer = getString(event.Data, "answer")
		}
		if answer != "" {
			v.lane.AddRow(0, "→ "+answer)
		}
	}
}

func (v *SwimlaneViz) View() string {
	return v.lane.View()
}
