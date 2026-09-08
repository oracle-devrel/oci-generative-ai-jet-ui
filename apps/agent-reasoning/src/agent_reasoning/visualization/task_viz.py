# src/visualization/task_viz.py
from typing import Dict

from rich.console import Group, RenderableType
from rich.panel import Panel
from rich.text import Text
from rich.tree import Tree

from .base import BaseVisualizer
from .models import StreamEvent, SubTask, TaskStatus


class TaskVisualizer(BaseVisualizer):
    """Visualizer for Decomposed/Least-to-Most - tree with status and progress bars."""

    STATUS_ICONS = {
        TaskStatus.PENDING: ("⏳", "dim"),
        TaskStatus.RUNNING: ("🔄", "yellow"),
        TaskStatus.COMPLETED: ("✅", "green"),
        TaskStatus.FAILED: ("❌", "red"),
    }

    def __init__(self, query: str = "", **kwargs):
        super().__init__(**kwargs)
        self.query = query
        self.tasks: Dict[int, SubTask] = {}

    def update(self, event: StreamEvent) -> None:
        if event.event_type == "task" and isinstance(event.data, SubTask):
            task = event.data
            self.tasks[task.id] = task
        elif event.event_type == "query" and isinstance(event.data, str):
            self.query = event.data

    def _make_progress_bar(self, progress: float, width: int = 20) -> str:
        filled = int(progress * width)
        empty = width - filled
        return f"[{'█' * filled}{'░' * empty}] {int(progress * 100)}%"

    def render(self) -> RenderableType:
        elements = []

        # Main task panel with overall progress
        completed = sum(1 for t in self.tasks.values() if t.status == TaskStatus.COMPLETED)
        total = len(self.tasks) or 1
        overall_progress = completed / total

        header_content = f"{self.query}\n\nProgress: {self._make_progress_bar(overall_progress)} ({completed}/{total} tasks)"

        elements.append(
            Panel(header_content, title="[bold cyan]Main Task[/bold cyan]", border_style="cyan")
        )

        if not self.tasks:
            elements.append(Text("Decomposing problem...", style="dim italic"))
            return Group(*elements)

        # Task tree
        tree = Tree("📋 Task Breakdown:")

        sorted_tasks = sorted(self.tasks.values(), key=lambda x: x.id)

        for task in sorted_tasks:
            icon, style = self.STATUS_ICONS.get(task.status, ("❓", "white"))

            # Task line with progress bar
            progress_bar = self._make_progress_bar(task.progress)
            task_text = Text()
            task_text.append(f"{icon} {task.id}. ", style=style)
            task_text.append(task.description)

            branch = tree.add(task_text)
            branch.add(Text(progress_bar, style=style))

            if task.result and task.status == TaskStatus.COMPLETED:
                result_preview = (
                    task.result[:100] + "..." if len(task.result) > 100 else task.result
                )
                branch.add(Text(f"Result: {result_preview}", style="dim"))
            elif task.status == TaskStatus.RUNNING and task.result:
                branch.add(Text(f"Currently: {task.result[:50]}...", style="yellow italic"))

        elements.append(tree)

        return Group(*elements)
