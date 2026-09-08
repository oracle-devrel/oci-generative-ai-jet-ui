package viz

import (
	"fmt"
	"strings"

	"agent-reasoning-tui/internal/client"
	"agent-reasoning-tui/internal/ui"

	"github.com/charmbracelet/lipgloss"
)

var (
	pipelineStageStyle = lipgloss.NewStyle().Bold(true).Foreground(lipgloss.Color("#FFFF00"))
	pipelineContentStyle = lipgloss.NewStyle().Foreground(lipgloss.Color("#CCCCCC"))
	pipelineScoreStyle   = lipgloss.NewStyle().Foreground(lipgloss.Color("#00FF00"))
)

type pipelineStage struct {
	name    string
	content string
	score   float64
}

// PipelineViz renders Complex Refinement pipeline events with a progress bar.
type PipelineViz struct {
	progress      *ui.ProgressBar
	stages        []pipelineStage
	stageNames    []string
	totalStages   int
	currentStage  int
	width, height int
}

func NewPipelineViz(width, height int) Visualizer {
	return &PipelineViz{
		width:  width,
		height: height,
	}
}

func (v *PipelineViz) Reset() {
	v.progress = nil
	v.stages = nil
	v.stageNames = nil
	v.totalStages = 0
	v.currentStage = 0
}

func (v *PipelineViz) SetSize(width, height int) {
	v.width = width
	v.height = height
	if v.progress != nil {
		v.progress = ui.NewProgressBar(v.stageNames, width)
		v.progress.SetCurrent(v.currentStage)
	}
}

func (v *PipelineViz) Update(event client.StructuredEvent) {
	switch event.EventType {
	case "pipeline":
		stageName := getString(event.Data, "stage_name")
		stageNum := getInt(event.Data, "stage_number")
		total := getInt(event.Data, "total_stages")
		content := getString(event.Data, "content")
		score := getFloat(event.Data, "score")

		if total > 0 && total != v.totalStages {
			v.totalStages = total
		}

		// Build stage names list on first event or when we get a new stage name
		if stageName != "" {
			found := false
			for _, sn := range v.stageNames {
				if sn == stageName {
					found = true
					break
				}
			}
			if !found {
				v.stageNames = append(v.stageNames, stageName)
			}
		}

		// Rebuild progress bar
		v.currentStage = stageNum - 1
		if v.currentStage < 0 {
			v.currentStage = 0
		}
		v.progress = ui.NewProgressBar(v.stageNames, v.width)
		v.progress.SetCurrent(v.currentStage)

		// Upsert stage content
		found := false
		for i, s := range v.stages {
			if s.name == stageName {
				v.stages[i].content = content
				v.stages[i].score = score
				found = true
				break
			}
		}
		if !found {
			v.stages = append(v.stages, pipelineStage{name: stageName, content: content, score: score})
		}

	case "final":
		content := getString(event.Data, "content")
		if content != "" {
			v.stages = append(v.stages, pipelineStage{name: "Final", content: content, score: 1.0})
			v.stageNames = append(v.stageNames, "Final")
			v.currentStage = len(v.stageNames) - 1
			if v.progress != nil {
				v.progress = ui.NewProgressBar(v.stageNames, v.width)
				v.progress.SetCurrent(v.currentStage)
			}
		}
	}
}

func (v *PipelineViz) View() string {
	if v.progress == nil {
		return "Waiting for pipeline stages..."
	}

	var lines []string
	lines = append(lines, v.progress.View())
	lines = append(lines, strings.Repeat("─", v.width))

	for _, stage := range v.stages {
		header := pipelineStageStyle.Render(stage.name)
		scoreStr := ""
		if stage.score > 0 {
			scoreStr = pipelineScoreStyle.Render(fmt.Sprintf(" [%.2f]", stage.score))
		}
		lines = append(lines, header+scoreStr)
		lines = append(lines, pipelineContentStyle.Render(wrapText(stage.content, v.width-2)))
		lines = append(lines, "")
	}

	return strings.Join(lines, "\n")
}
