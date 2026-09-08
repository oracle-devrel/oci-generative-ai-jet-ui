package viz

// Registry maps agent IDs to visualizer constructors.
var Registry = map[string]func(int, int) Visualizer{
	"cot":                NewStepsViz,
	"tot":                NewTreeViz,
	"mcts":               NewTreeViz,
	"react":              NewSwimlaneViz,
	"consistency":        NewVotingViz,
	"reflection":         NewDiffViz,
	"refinement":         NewDiffViz,
	"complex_refinement": NewPipelineViz,
	"debate":             NewDebateViz,
	"socratic":           NewSocraticViz,
	"analogical":         NewAnalogyViz,
	"decomposed":         NewTaskTreeViz,
	"least_to_most":      NewTaskTreeViz,
}

// GetVisualizer returns a new Visualizer for the given agentID, or nil if unsupported.
func GetVisualizer(agentID string, width, height int) Visualizer {
	if ctor, ok := Registry[agentID]; ok {
		return ctor(width, height)
	}
	return nil
}
