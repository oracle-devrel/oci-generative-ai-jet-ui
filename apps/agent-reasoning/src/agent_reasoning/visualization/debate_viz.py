# src/visualization/debate_viz.py
from typing import Dict

from rich.console import Group, RenderableType
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .base import BaseVisualizer
from .models import DebateRound, StreamEvent


class DebateVisualizer(BaseVisualizer):
    """Visualizer for Adversarial Debate - side-by-side pro/con with judge scoring."""

    def __init__(self, query: str = "", rounds: int = 3, **kwargs):
        super().__init__(**kwargs)
        self.query = query
        self.rounds_config = rounds
        self.rounds: Dict[int, DebateRound] = {}
        self.final_answer: str = ""

    def update(self, event: StreamEvent) -> None:
        if event.event_type == "debate_round" and isinstance(event.data, DebateRound):
            self.rounds[event.data.round_num] = event.data
        elif event.event_type == "query" and isinstance(event.data, str):
            self.query = event.data
        elif event.event_type == "final" and isinstance(event.data, str):
            self.final_answer = event.data

    def render(self) -> RenderableType:
        elements = []

        # Header
        elements.append(
            Panel(
                f"Topic: {self.query}",
                title=f"[bold red]Adversarial Debate ({self.rounds_config} rounds)[/bold red]",
                border_style="red",
            )
        )

        if not self.rounds:
            elements.append(Text("Preparing debate...", style="dim italic"))
            return Group(*elements)

        for round_num in sorted(self.rounds.keys()):
            rnd = self.rounds[round_num]

            # Debate table
            table = Table(show_header=True, expand=True, title=f"Round {round_num}")
            table.add_column("PRO", style="green", width=35)
            table.add_column("CON", style="red", width=35)

            pro = (
                rnd.pro_argument[:200] + "..." if len(rnd.pro_argument) > 200 else rnd.pro_argument
            )
            con = (
                rnd.con_argument[:200] + "..." if len(rnd.con_argument) > 200 else rnd.con_argument
            )
            table.add_row(pro or "Preparing...", con or "Waiting...")
            elements.append(table)

            # Judge score bar
            if rnd.winner:
                pro_bar = int(rnd.judge_score_pro * 3)
                con_bar = int(rnd.judge_score_con * 3)
                winner_str = f"[bold]Winner: {rnd.winner.upper()}[/bold]"
                score_str = (
                    f"[green]PRO: {rnd.judge_score_pro:.1f}/10 {'|' * pro_bar}[/green]  "
                    f"[red]CON: {rnd.judge_score_con:.1f}/10 {'|' * con_bar}[/red]  "
                    f"{winner_str}"
                )
                commentary = rnd.judge_commentary[:150] if rnd.judge_commentary else ""
                elements.append(
                    Panel(
                        f"{score_str}\n{commentary}",
                        title="[bold yellow]Judge[/bold yellow]",
                        border_style="yellow",
                        padding=(0, 1),
                    )
                )

        if self.final_answer:
            elements.append(
                Panel(
                    self.final_answer[:500],
                    title="[bold green]Final Synthesis[/bold green]",
                    border_style="green",
                )
            )

        return Group(*elements)
