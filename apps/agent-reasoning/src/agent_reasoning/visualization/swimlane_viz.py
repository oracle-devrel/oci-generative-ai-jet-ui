# src/visualization/swimlane_viz.py
from typing import Dict

from rich.console import Group, RenderableType
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .base import BaseVisualizer
from .models import ReActStep, StreamEvent, TaskStatus


class SwimlaneVisualizer(BaseVisualizer):
    """Visualizer for ReAct - three-track thought/action/observation."""

    def __init__(self, query: str = "", max_steps: int = 5, **kwargs):
        super().__init__(**kwargs)
        self.query = query
        self.max_steps = max_steps
        self.steps: Dict[int, ReActStep] = {}
        self.final_answer: str = ""
        self.tool_usage: Dict[str, int] = {}

    def update(self, event: StreamEvent) -> None:
        if event.event_type == "react_step" and isinstance(event.data, ReActStep):
            step = event.data
            self.steps[step.step] = step
            if step.action:
                self.tool_usage[step.action] = self.tool_usage.get(step.action, 0) + 1
        elif event.event_type == "query" and isinstance(event.data, str):
            self.query = event.data
        elif event.event_type == "final_answer" and isinstance(event.data, str):
            self.final_answer = event.data

    def render(self) -> RenderableType:
        elements = []

        # Header
        elements.append(
            Panel(
                f"Query: {self.query}",
                title="[bold cyan]ReAct Agent (Reason + Act)[/bold cyan]",
                border_style="cyan",
            )
        )

        if not self.steps:
            elements.append(Text("Thinking...", style="dim italic"))
            return Group(*elements)

        # Render each step as a swimlane table
        for step_num in sorted(self.steps.keys()):
            step = self.steps[step_num]

            table = Table(show_header=True, expand=True, title=f"Step {step_num}/{self.max_steps}")
            table.add_column("🧠 Thought", style="blue", width=25)
            table.add_column("🔧 Action", style="yellow", width=20)
            table.add_column("👁 Observation", style="green", width=25)

            thought = step.thought[:100] + "..." if len(step.thought) > 100 else step.thought

            if step.action:
                action = f"{step.action}\n[{step.action_input}]"
            else:
                action = "─"

            if step.observation:
                obs = (
                    step.observation[:100] + "..."
                    if len(step.observation) > 100
                    else step.observation
                )
            elif step.status == TaskStatus.RUNNING:
                obs = "⏳ Waiting..."
            else:
                obs = "─"

            table.add_row(thought, action, obs)
            elements.append(table)

            # Arrow between steps
            if step_num < max(self.steps.keys()):
                elements.append(Text("                    │\n                    ▼", style="dim"))

        # Final answer
        if self.final_answer:
            tool_summary = "  ".join(
                [
                    f"{tool}: {count} call{'s' if count > 1 else ''} ✅"
                    for tool, count in self.tool_usage.items()
                ]
            )

            elements.append(
                Panel(
                    f"{self.final_answer}\n\n[dim]Tool Usage: {tool_summary}[/dim]",
                    title="[bold green]🎯 Final Answer[/bold green]",
                    border_style="green",
                )
            )

        return Group(*elements)
