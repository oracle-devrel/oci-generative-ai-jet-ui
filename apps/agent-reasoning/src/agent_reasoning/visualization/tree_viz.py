# src/visualization/tree_viz.py
from typing import Dict, Optional

from rich.console import Group, RenderableType
from rich.panel import Panel
from rich.text import Text

from .base import BaseVisualizer
from .models import StreamEvent, TreeNode


class TreeVisualizer(BaseVisualizer):
    """Visualizer for Tree of Thoughts - nested panels with color-coded scores."""

    def __init__(self, query: str = "", **kwargs):
        super().__init__(**kwargs)
        self.query = query
        self.nodes: Dict[str, TreeNode] = {}
        self.best_path: set = set()

    def _score_to_color(self, score: Optional[float]) -> str:
        if score is None:
            return "white"
        if score >= 0.8:
            return "green"
        if score >= 0.5:
            return "yellow"
        return "red"

    def _score_to_style(self, score: Optional[float], is_best: bool, is_pruned: bool) -> str:
        if is_pruned:
            return "dim red"
        if is_best:
            return "bold green"
        return self._score_to_color(score)

    def update(self, event: StreamEvent) -> None:
        if event.event_type == "node" and isinstance(event.data, TreeNode):
            node = event.data
            self.nodes[node.id] = node
            if node.is_best:
                self.best_path.add(node.id)
        elif event.event_type == "query" and isinstance(event.data, str):
            self.query = event.data

    def _build_subtree(self, parent_id: Optional[str], depth: int = 0) -> list:
        """Recursively build tree structure."""
        children = [n for n in self.nodes.values() if n.parent_id == parent_id]
        children.sort(key=lambda x: x.score or 0, reverse=True)
        return children

    def render(self) -> RenderableType:
        elements = []

        # Query panel
        if self.query:
            elements.append(
                Panel(self.query, title="[bold cyan]Query[/bold cyan]", border_style="cyan")
            )

        if not self.nodes:
            elements.append(Text("Thinking...", style="dim italic"))
            return Group(*elements)

        # Build tree by depth
        max_depth = max((n.depth for n in self.nodes.values()), default=0)

        for depth in range(1, max_depth + 1):
            depth_nodes = [n for n in self.nodes.values() if n.depth == depth]
            if not depth_nodes:
                continue

            depth_panels = []
            for node in sorted(depth_nodes, key=lambda x: x.id):
                score_str = f"[{node.score:.2f}]" if node.score is not None else ""
                best_marker = " ★" if node.is_best else ""
                pruned_marker = " (pruned)" if node.is_pruned else ""

                style = self._score_to_style(node.score, node.is_best, node.is_pruned)
                title = f"Branch {node.id} {score_str}{best_marker}{pruned_marker}"

                content = node.content[:200] + "..." if len(node.content) > 200 else node.content

                depth_panels.append(
                    Panel(
                        Text(content, style="dim" if node.is_pruned else ""),
                        title=f"[{style}]{title}[/{style}]",
                        border_style=style,
                        padding=(0, 1),
                    )
                )

            elements.append(
                Panel(
                    Group(*depth_panels), title=f"[bold]Depth {depth}[/bold]", border_style="blue"
                )
            )

        return Group(*elements)
