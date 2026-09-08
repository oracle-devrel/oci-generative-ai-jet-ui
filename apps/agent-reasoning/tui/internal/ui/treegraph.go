package ui

import (
	"fmt"
	"strings"

	"github.com/charmbracelet/lipgloss"
)

// NodeStatus represents the state of a tree node.
type NodeStatus int

const (
	NodePending NodeStatus = iota
	NodeActive
	NodeDone
	NodePruned
	NodeError
)

var nodeStatusIcon = map[NodeStatus]string{
	NodePending: "○",
	NodeActive:  "●",
	NodeDone:    "✓",
	NodePruned:  "✗",
	NodeError:   "⚠",
}

var (
	treeHighlightStyle = lipgloss.NewStyle().Foreground(lipgloss.Color("#00FFFF")).Bold(true)
	treePrunedStyle    = lipgloss.NewStyle().Foreground(lipgloss.Color("#666666"))
	treeDoneStyle      = lipgloss.NewStyle().Foreground(lipgloss.Color("#00FF00"))
	treeActiveStyle    = lipgloss.NewStyle().Foreground(lipgloss.Color("#FFFF00"))
	treeErrorStyle     = lipgloss.NewStyle().Foreground(lipgloss.Color("#FF0000"))
	treeDefaultStyle   = lipgloss.NewStyle()
)

// TreeGraphNode is a node in the tree.
type TreeGraphNode struct {
	Label       string
	Content     string
	Score       float64
	Status      NodeStatus
	Children    []*TreeGraphNode
	Highlighted bool
	Depth       int
}

// TreeGraph renders tree data structures with box-drawing characters.
type TreeGraph struct {
	root          *TreeGraphNode
	width, height int
}

func NewTreeGraph(root *TreeGraphNode, width, height int) *TreeGraph {
	return &TreeGraph{root: root, width: width, height: height}
}

// HighlightPath marks all ancestors from root to target as highlighted.
func (g *TreeGraph) HighlightPath(target *TreeGraphNode) {
	var mark func(node *TreeGraphNode) bool
	mark = func(node *TreeGraphNode) bool {
		if node == nil {
			return false
		}
		if node == target {
			node.Highlighted = true
			return true
		}
		for _, child := range node.Children {
			if mark(child) {
				node.Highlighted = true
				return true
			}
		}
		return false
	}
	mark(g.root)
}

// View renders the tree with box-drawing connectors.
func (g *TreeGraph) View() string {
	if g.root == nil {
		return ""
	}
	var lines []string
	renderNode(g.root, "", true, true, &lines)

	// Truncate to height
	if g.height > 0 && len(lines) > g.height {
		lines = lines[:g.height]
		lines = append(lines, treePrunedStyle.Render("... (truncated)"))
	}

	// Truncate each line to width using lipgloss's ANSI-aware width measurement
	result := make([]string, len(lines))
	for i, line := range lines {
		if g.width > 0 && lipgloss.Width(line) > g.width {
			// Strip to plain runes and truncate
			plain := ansiStrip(line)
			runes := []rune(plain)
			if len(runes) > g.width {
				runes = runes[:g.width]
			}
			result[i] = string(runes)
		} else {
			result[i] = line
		}
	}
	return strings.Join(result, "\n")
}

// renderNode renders a tree node recursively.
// prefix is the indentation string prepended before the connector.
// isRoot marks the top-level node (no connector drawn).
func renderNode(node *TreeGraphNode, prefix string, isLast bool, isRoot bool, lines *[]string) {
	connector := "├── "
	continuation := "│   "
	if isLast {
		connector = "└── "
		continuation = "    "
	}

	icon := nodeStatusIcon[node.Status]
	label := node.Label
	scorePart := ""
	if node.Score > 0 {
		scorePart = fmt.Sprintf(" [%.2f]", node.Score)
	}

	nodeText := icon + " " + label + scorePart

	var styled string
	switch {
	case node.Highlighted:
		styled = treeHighlightStyle.Render(nodeText)
	case node.Status == NodePruned:
		styled = treePrunedStyle.Render(nodeText)
	case node.Status == NodeDone:
		styled = treeDoneStyle.Render(nodeText)
	case node.Status == NodeActive:
		styled = treeActiveStyle.Render(nodeText)
	case node.Status == NodeError:
		styled = treeErrorStyle.Render(nodeText)
	default:
		styled = treeDefaultStyle.Render(nodeText)
	}

	var line string
	if isRoot {
		line = styled
	} else {
		line = prefix + connector + styled
	}
	*lines = append(*lines, line)

	var childPrefix string
	if isRoot {
		childPrefix = ""
	} else {
		childPrefix = prefix + continuation
	}
	for i, child := range node.Children {
		last := i == len(node.Children)-1
		renderNode(child, childPrefix, last, false, lines)
	}
}
