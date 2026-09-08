# src/visualization/voting_viz.py
from collections import Counter
from typing import Dict

from rich.console import Group, RenderableType
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .base import BaseVisualizer
from .models import StreamEvent, TaskStatus, VotingSample


class VotingVisualizer(BaseVisualizer):
    """Visualizer for Self-Consistency - side-by-side columns with vote tallies."""

    SAMPLE_COLORS = ["blue", "green", "magenta", "yellow", "red"]
    SAMPLE_ICONS = ["🔵", "🟢", "🟣", "🟠", "🔴"]

    def __init__(self, query: str = "", k: int = 5, **kwargs):
        super().__init__(**kwargs)
        self.query = query
        self.k = k
        self.samples: Dict[int, VotingSample] = {}
        self.voting_complete = False

    def update(self, event: StreamEvent) -> None:
        if event.event_type == "sample" and isinstance(event.data, VotingSample):
            sample = event.data
            self.samples[sample.id] = sample
        elif event.event_type == "query" and isinstance(event.data, str):
            self.query = event.data
        elif event.event_type == "voting_complete":
            self.voting_complete = True

    def _make_progress_bar(self, current: int, total: int, width: int = 20) -> str:
        filled = int((current / total) * width) if total > 0 else 0
        empty = width - filled
        return f"[{'█' * filled}{'░' * empty}] {current}/{total}"

    def render(self) -> RenderableType:
        elements = []

        # Header
        elements.append(
            Panel(
                f"Query: {self.query}",
                title=f"[bold cyan]Self-Consistency Voting (k={self.k})[/bold cyan]",
                border_style="cyan",
            )
        )

        # Sampling progress
        completed = sum(1 for s in self.samples.values() if s.status == TaskStatus.COMPLETED)
        progress_text = f"Sampling Progress: {self._make_progress_bar(completed, self.k)} complete"
        elements.append(Text(progress_text))
        elements.append(Text(""))

        if not self.samples:
            elements.append(Text("Starting samples...", style="dim italic"))
            return Group(*elements)

        # Samples table
        table = Table(show_header=True, header_style="bold", expand=True)

        for i in range(min(len(self.samples), self.k)):
            color = self.SAMPLE_COLORS[i % len(self.SAMPLE_COLORS)]
            icon = self.SAMPLE_ICONS[i % len(self.SAMPLE_ICONS)]

            sample = self.samples.get(i + 1)
            if sample:
                status = (
                    "✅ Complete" if sample.status == TaskStatus.COMPLETED else "🔄 Streaming..."
                )
                header = f"{icon} Sample {i + 1}\n{status}"
            else:
                header = f"{icon} Sample {i + 1}\n⏳ Pending"

            table.add_column(header, style=color, width=25)

        # Add reasoning rows
        row_data = []
        for i in range(min(len(self.samples), self.k)):
            sample = self.samples.get(i + 1)
            if sample:
                reasoning = (
                    sample.reasoning[:150] + "..."
                    if len(sample.reasoning) > 150
                    else sample.reasoning
                )
                cell = f"{reasoning}\n\nFinal Answer:\n{sample.answer}"
            else:
                cell = "(waiting)"
            row_data.append(cell)

        if row_data:
            table.add_row(*row_data)

        # Vote row
        vote_row = []
        for i in range(min(len(self.samples), self.k)):
            sample = self.samples.get(i + 1)
            icon = self.SAMPLE_ICONS[i % len(self.SAMPLE_ICONS)]
            if sample and sample.answer:
                vote_row.append(f"{icon} Vote: {sample.answer}")
            else:
                vote_row.append("")

        if vote_row:
            table.add_row(*vote_row)

        elements.append(table)

        # Voting results
        if self.voting_complete and self.samples:
            answers = [s.answer for s in self.samples.values() if s.answer]
            if answers:
                counter = Counter(answers)
                total_votes = len(answers)

                results = []
                for answer, count in counter.most_common():
                    bar_width = int((count / total_votes) * 30)
                    is_winner = count == counter.most_common(1)[0][1]
                    color = "green" if is_winner else "red"
                    marker = "✓ WINNER" if is_winner and count > total_votes / 2 else ""
                    results.append(
                        f"[{color}]   {answer}  {'█' * bar_width}  {count} votes  {marker}[/{color}]"
                    )

                consensus = (
                    "UNANIMOUS"
                    if len(counter) == 1
                    else f"MAJORITY ({counter.most_common(1)[0][1]}/{total_votes})"
                )
                results.append(f"\nConsensus: {consensus}")

                elements.append(
                    Panel(
                        "\n".join(results),
                        title="[bold]🗳️  Voting Results[/bold]",
                        border_style="yellow",
                    )
                )

        return Group(*elements)
