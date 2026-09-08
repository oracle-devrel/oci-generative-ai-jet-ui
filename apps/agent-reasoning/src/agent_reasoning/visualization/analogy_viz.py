# src/visualization/analogy_viz.py
from typing import List

from rich.console import Group, RenderableType
from rich.panel import Panel
from rich.text import Text

from .base import BaseVisualizer
from .models import AnalogyMapping, StreamEvent


class AnalogyVisualizer(BaseVisualizer):
    """Visualizer for Analogical Reasoning - three-phase panel."""

    PHASE_ICONS = {"identify": "?", "generate": "*", "transfer": "->"}
    PHASE_COLORS = {"identify": "blue", "generate": "yellow", "transfer": "green"}

    def __init__(self, query: str = "", **kwargs):
        super().__init__(**kwargs)
        self.query = query
        self.mappings: List[AnalogyMapping] = []
        self.current_phase = "identify"
        self.final_answer: str = ""

    def update(self, event: StreamEvent) -> None:
        if event.event_type == "analogy" and isinstance(event.data, AnalogyMapping):
            mapping = event.data
            self.current_phase = mapping.phase
            if event.is_update and self.mappings:
                self.mappings[-1] = mapping
            else:
                self.mappings.append(mapping)
        elif event.event_type == "query" and isinstance(event.data, str):
            self.query = event.data
        elif event.event_type == "final" and isinstance(event.data, str):
            self.final_answer = event.data

    def render(self) -> RenderableType:
        elements = []

        # Header
        elements.append(
            Panel(
                f"Problem: {self.query}",
                title="[bold yellow]Analogical Reasoning[/bold yellow]",
                border_style="yellow",
            )
        )

        # Phase indicators
        phases = ["identify", "generate", "transfer"]
        phase_texts = []
        for p in phases:
            icon = self.PHASE_ICONS[p]
            color = self.PHASE_COLORS[p]
            active = "bold" if p == self.current_phase else "dim"
            phase_texts.append(f"[{active} {color}]{icon} {p.title()}[/{active} {color}]")
        elements.append(Text.from_markup("  ->  ".join(phase_texts)))
        elements.append(Text(""))

        # Show content for completed/active phases
        for mapping in self.mappings:
            if mapping.phase == "identify" and mapping.abstract_structure:
                content = mapping.abstract_structure[:300]
                elements.append(
                    Panel(
                        content,
                        title="[blue]Abstract Structure[/blue]",
                        border_style="blue",
                        padding=(0, 1),
                    )
                )

            if mapping.phase == "generate" and mapping.source_domain:
                content = mapping.source_domain[:300]
                elements.append(
                    Panel(
                        content,
                        title="[yellow]Analogies[/yellow]",
                        border_style="yellow",
                        padding=(0, 1),
                    )
                )

            if mapping.phase == "transfer" and mapping.solution_transfer:
                content = mapping.solution_transfer[:300]
                elements.append(
                    Panel(
                        content,
                        title="[green]Solution Transfer[/green]",
                        border_style="green",
                        padding=(0, 1),
                    )
                )

        if self.final_answer:
            elements.append(
                Panel(
                    self.final_answer[:500],
                    title="[bold green]Final Answer[/bold green]",
                    border_style="green",
                )
            )

        if not self.mappings:
            elements.append(Text("Analyzing problem structure...", style="dim italic"))

        return Group(*elements)
