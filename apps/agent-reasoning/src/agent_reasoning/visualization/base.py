# src/visualization/base.py
from abc import ABC, abstractmethod
from typing import Generator

from rich.console import Console, RenderableType
from rich.live import Live

from .models import StreamEvent


class BaseVisualizer(ABC):
    """Base class for all visualizers."""

    def __init__(self, console: Console = None):
        self.console = console or Console()
        self.state = {}

    @abstractmethod
    def render(self) -> RenderableType:
        """Return current Rich renderable for the visualization state."""
        pass

    @abstractmethod
    def update(self, event: StreamEvent) -> None:
        """Update internal state with new event."""
        pass

    def reset(self) -> None:
        """Reset visualizer state."""
        self.state = {}

    def run(self, event_stream: Generator[StreamEvent, None, None]) -> None:
        """Run visualization with live updates."""
        with Live(
            self.render(), console=self.console, refresh_per_second=10, vertical_overflow="visible"
        ) as live:
            for event in event_stream:
                self.update(event)
                live.update(self.render())
