# src/visualization/step_viz.py
import re
from typing import Dict

from rich.console import Group, RenderableType
from rich.panel import Panel
from rich.text import Text

from .base import BaseVisualizer
from .models import ChainStep, StreamEvent


class StepVisualizer(BaseVisualizer):
    """Visualizer for Chain-of-Thought - numbered step panels with flow arrows."""

    STEP_ICONS = {
        "calculate": "🔢",
        "time": "⏱️",
        "divide": "➗",
        "analyze": "🔍",
        "conclude": "💡",
        "final": "✅",
        "default": "📌",
    }

    def __init__(self, query: str = "", **kwargs):
        super().__init__(**kwargs)
        self.query = query
        self.steps: Dict[int, ChainStep] = {}
        self.raw_content = ""
        self.final_answer = ""

    def _detect_icon(self, content: str) -> str:
        content_lower = content.lower()
        if any(w in content_lower for w in ["calculate", "compute", "multiply", "add", "subtract"]):
            return self.STEP_ICONS["calculate"]
        if any(w in content_lower for w in ["time", "hour", "minute", "second", "duration"]):
            return self.STEP_ICONS["time"]
        if any(w in content_lower for w in ["divide", "split", "ratio"]):
            return self.STEP_ICONS["divide"]
        if any(w in content_lower for w in ["analyze", "examine", "consider", "look"]):
            return self.STEP_ICONS["analyze"]
        if any(w in content_lower for w in ["therefore", "conclude", "result", "answer"]):
            return self.STEP_ICONS["conclude"]
        return self.STEP_ICONS["default"]

    def update(self, event: StreamEvent) -> None:
        if event.event_type == "chain_step" and isinstance(event.data, ChainStep):
            step = event.data
            step.icon = self._detect_icon(step.content)
            self.steps[step.step] = step
        elif event.event_type == "query" and isinstance(event.data, str):
            self.query = event.data
        elif event.event_type == "raw_content" and isinstance(event.data, str):
            self.raw_content = event.data
        elif event.event_type == "final_answer" and isinstance(event.data, str):
            self.final_answer = event.data

    def _parse_steps_from_raw(self) -> None:
        """Parse steps from raw content if not already structured."""
        if self.steps:
            return

        # Try to split by step markers
        patterns = [
            r"(?:Step\s+)?(\d+)[\.:\)]\s*(.+?)(?=(?:Step\s+)?\d+[\.:\)]|$)",
            r"(First|Second|Third|Next|Finally)[,:]?\s*(.+?)(?=(?:First|Second|Third|Next|Finally)[,:]|$)",
        ]

        for pattern in patterns:
            matches = re.findall(pattern, self.raw_content, re.IGNORECASE | re.DOTALL)
            if matches:
                for i, (_, content) in enumerate(matches, 1):
                    self.steps[i] = ChainStep(
                        step=i, content=content.strip(), icon=self._detect_icon(content)
                    )
                break

    def render(self) -> RenderableType:
        elements = []

        # Header
        elements.append(
            Panel(
                f"Query: {self.query}",
                title="[bold cyan]Chain-of-Thought Reasoning[/bold cyan]",
                border_style="cyan",
            )
        )

        # Try to parse if we have raw content but no steps
        if self.raw_content and not self.steps:
            self._parse_steps_from_raw()

        if not self.steps and not self.raw_content:
            elements.append(Text("Thinking step by step...", style="dim italic"))
            return Group(*elements)

        # If we have structured steps, render them
        if self.steps:
            total = len(self.steps)
            for step_num in sorted(self.steps.keys()):
                step = self.steps[step_num]

                content = step.content[:300] + "..." if len(step.content) > 300 else step.content

                elements.append(
                    Panel(
                        f"{step.icon} {content}",
                        title=f"[bold]Step {step_num}[/bold]",
                        border_style="blue",
                    )
                )

                # Arrow between steps
                if step_num < total:
                    elements.append(
                        Text(
                            "                          │\n                          ▼", style="dim"
                        )
                    )

            # Progress
            elements.append(
                Text(
                    f"\nReasoning Progress: {'●───' * len(self.steps)}● {len(self.steps)}/{len(self.steps)}",
                    style="dim",
                )
            )
        else:
            # Fallback to raw content
            elements.append(
                Panel(self.raw_content, title="[bold]Reasoning[/bold]", border_style="blue")
            )

        # Final answer
        if self.final_answer:
            elements.append(
                Panel(
                    self.final_answer,
                    title="[bold green]🎯 Final Answer[/bold green]",
                    border_style="green",
                )
            )

        return Group(*elements)
