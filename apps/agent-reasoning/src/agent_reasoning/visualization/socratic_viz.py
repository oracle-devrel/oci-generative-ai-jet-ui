# src/visualization/socratic_viz.py
from typing import Dict

from rich.console import Group, RenderableType
from rich.panel import Panel
from rich.text import Text
from rich.tree import Tree

from .base import BaseVisualizer
from .models import SocraticExchange, StreamEvent


class SocraticVisualizer(BaseVisualizer):
    """Visualizer for Socratic Method - threaded Q&A converging to answer."""

    def __init__(self, query: str = "", max_questions: int = 5, **kwargs):
        super().__init__(**kwargs)
        self.query = query
        self.max_questions = max_questions
        self.exchanges: Dict[int, SocraticExchange] = {}
        self.final_answer: str = ""

    def update(self, event: StreamEvent) -> None:
        if event.event_type == "socratic" and isinstance(event.data, SocraticExchange):
            self.exchanges[event.data.question_num] = event.data
        elif event.event_type == "query" and isinstance(event.data, str):
            self.query = event.data
        elif event.event_type == "final" and isinstance(event.data, str):
            self.final_answer = event.data

    def render(self) -> RenderableType:
        elements = []

        # Header
        completed = sum(1 for e in self.exchanges.values() if e.answer and not e.is_final_synthesis)
        elements.append(
            Panel(
                f"Question: {self.query}\n"
                f"Progress: {completed}/{self.max_questions} sub-questions answered",
                title="[bold cyan]Socratic Method[/bold cyan]",
                border_style="cyan",
            )
        )

        if not self.exchanges:
            elements.append(Text("Formulating first question...", style="dim italic"))
            return Group(*elements)

        # Q&A tree
        tree = Tree("[bold]Inquiry Chain[/bold]")
        for qnum in sorted(self.exchanges.keys()):
            exchange = self.exchanges[qnum]
            if exchange.is_final_synthesis:
                continue

            q_text = exchange.question[:100] if exchange.question else "Thinking..."
            branch = tree.add(f"[bold cyan]Q{qnum}:[/bold cyan] {q_text}")

            if exchange.answer:
                a_text = (
                    exchange.answer[:100] + "..." if len(exchange.answer) > 100 else exchange.answer
                )
                branch.add(f"[green]A:[/green] {a_text}")

            if exchange.narrows_to:
                branch.add(f"[dim yellow]-> {exchange.narrows_to}[/dim yellow]")

        elements.append(tree)

        # Final synthesis
        synthesis = next((e for e in self.exchanges.values() if e.is_final_synthesis), None)
        if synthesis and synthesis.answer:
            elements.append(
                Panel(
                    synthesis.answer[:500],
                    title="[bold green]Synthesis[/bold green]",
                    border_style="green",
                )
            )
        elif self.final_answer:
            elements.append(
                Panel(
                    self.final_answer[:500],
                    title="[bold green]Final Answer[/bold green]",
                    border_style="green",
                )
            )

        return Group(*elements)
