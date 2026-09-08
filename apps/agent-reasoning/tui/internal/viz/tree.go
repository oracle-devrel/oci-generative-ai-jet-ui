package viz

import (
	"agent-reasoning-tui/internal/client"
	"agent-reasoning-tui/internal/ui"
)

// TreeViz renders ToT/MCTS node events using the TreeGraph primitive.
type TreeViz struct {
	root          *ui.TreeGraphNode
	nodes         map[string]*ui.TreeGraphNode
	graph         *ui.TreeGraph
	width, height int
}

func NewTreeViz(width, height int) Visualizer {
	return &TreeViz{
		nodes:  make(map[string]*ui.TreeGraphNode),
		width:  width,
		height: height,
	}
}

func (v *TreeViz) Reset() {
	v.root = nil
	v.nodes = make(map[string]*ui.TreeGraphNode)
	v.graph = nil
}

func (v *TreeViz) SetSize(width, height int) {
	v.width = width
	v.height = height
	if v.graph != nil {
		v.graph = ui.NewTreeGraph(v.root, width, height)
	}
}

func (v *TreeViz) Update(event client.StructuredEvent) {
	switch event.EventType {
	case "node":
		id := getString(event.Data, "id")
		if id == "" {
			return
		}

		score := getFloat(event.Data, "score")
		content := getString(event.Data, "content")
		depth := getInt(event.Data, "depth")

		if event.IsUpdate {
			// Update existing node score/status
			if n, ok := v.nodes[id]; ok {
				n.Score = score
				if score > 0.7 {
					n.Status = ui.NodeDone
				}
			}
			return
		}

		node := &ui.TreeGraphNode{
			Label:   truncateLabel(content, 30),
			Content: content,
			Score:   score,
			Status:  ui.NodeActive,
			Depth:   depth,
		}
		v.nodes[id] = node

		// First node becomes root
		if v.root == nil {
			v.root = node
			node.Status = ui.NodeDone
		} else {
			// Attach to parent based on depth heuristic: find node at depth-1
			parentID := getString(event.Data, "parent_id")
			if parentID != "" {
				if parent, ok := v.nodes[parentID]; ok {
					parent.Children = append(parent.Children, node)
				} else {
					v.root.Children = append(v.root.Children, node)
				}
			} else {
				// Find deepest node at depth-1 as parent
				v.attachByDepth(node, depth)
			}
		}

		v.graph = ui.NewTreeGraph(v.root, v.width, v.height)

	case "final":
		// Highlight the best path — find node with highest score
		var best *ui.TreeGraphNode
		for _, n := range v.nodes {
			if best == nil || n.Score > best.Score {
				best = n
			}
		}
		if best != nil && v.graph != nil {
			best.Status = ui.NodeDone
			v.graph.HighlightPath(best)
		}
	}
}

func (v *TreeViz) View() string {
	if v.graph == nil || v.root == nil {
		return "Waiting for tree nodes..."
	}
	return v.graph.View()
}

// attachByDepth attaches node to the most recently added node at depth-1.
func (v *TreeViz) attachByDepth(node *ui.TreeGraphNode, depth int) {
	if depth <= 1 {
		v.root.Children = append(v.root.Children, node)
		return
	}
	// Find any node at depth-1 (last one wins)
	var parent *ui.TreeGraphNode
	for _, n := range v.nodes {
		if n.Depth == depth-1 {
			parent = n
		}
	}
	if parent != nil {
		parent.Children = append(parent.Children, node)
	} else {
		v.root.Children = append(v.root.Children, node)
	}
}

func truncateLabel(s string, max int) string {
	runes := []rune(s)
	if len(runes) <= max {
		return s
	}
	return string(runes[:max-3]) + "..."
}
