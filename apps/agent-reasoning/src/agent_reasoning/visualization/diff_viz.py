# src/visualization/diff_viz.py
import difflib
from typing import Dict, Union

from rich.console import Group, RenderableType
from rich.panel import Panel
from rich.text import Text

from .base import BaseVisualizer
from .models import RefinementIteration, ReflectionIteration, StreamEvent


class DiffVisualizer(BaseVisualizer):
    """Visualizer for Self-Reflection and Refinement Loop - iterations with diff highlighting."""

    def __init__(self, query: str = "", max_iterations: int = 10, **kwargs):
        super().__init__(**kwargs)
        self.query = query
        self.max_iterations = max_iterations
        self.iterations: Dict[int, Union[ReflectionIteration, RefinementIteration]] = {}
        self.current_phase = "draft"  # draft, critique, improvement
        self.mode = "reflection"  # reflection or refinement

    def update(self, event: StreamEvent) -> None:
        if event.event_type == "iteration" and isinstance(event.data, ReflectionIteration):
            iteration = event.data
            self.iterations[iteration.iteration] = iteration
            self.mode = "reflection"
        elif event.event_type == "refinement" and isinstance(event.data, RefinementIteration):
            iteration = event.data
            self.iterations[iteration.iteration] = iteration
            self.mode = "refinement"
        elif event.event_type == "query" and isinstance(event.data, str):
            self.query = event.data
        elif event.event_type == "phase" and isinstance(event.data, str):
            self.current_phase = event.data

    def _compute_diff(self, old_text: str, new_text: str) -> Text:
        """Compute word-level diff with highlighting."""
        result = Text()

        old_words = old_text.split()
        new_words = new_text.split()

        matcher = difflib.SequenceMatcher(None, old_words, new_words)

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == "equal":
                result.append(" ".join(old_words[i1:i2]) + " ")
            elif tag == "replace":
                result.append(" ".join(new_words[j1:j2]) + " ", style="bold green on dark_green")
            elif tag == "insert":
                result.append(" ".join(new_words[j1:j2]) + " ", style="bold green on dark_green")
            elif tag == "delete":
                pass  # Don't show deleted in final version

        return result

    def _make_iteration_progress(self) -> str:
        if self.mode == "refinement":
            len(
                [
                    i
                    for i in self.iterations.values()
                    if isinstance(i, RefinementIteration) and i.is_accepted
                ]
            )
        else:
            len(
                [
                    i
                    for i in self.iterations.values()
                    if isinstance(i, ReflectionIteration) and (i.is_correct or i.improvement)
                ]
            )
        dots = [
            "●" if i <= len(self.iterations) else "○" for i in range(1, self.max_iterations + 1)
        ]
        return "───".join(dots) + f" {len(self.iterations)}/{self.max_iterations}"

    def _is_iteration_complete(self, iteration) -> bool:
        """Check if an iteration is complete (accepted or correct)."""
        if isinstance(iteration, RefinementIteration):
            return iteration.is_accepted
        elif isinstance(iteration, ReflectionIteration):
            return iteration.is_correct
        return False

    def render(self) -> RenderableType:
        elements = []

        # Header
        if self.mode == "refinement":
            title = "[bold cyan]Refinement Loop (score-based)[/bold cyan]"
        else:
            title = f"[bold cyan]Self-Reflection (max {self.max_iterations} iterations)[/bold cyan]"

        elements.append(Panel(f"Query: {self.query}", title=title, border_style="cyan"))

        if not self.iterations:
            elements.append(Text("Drafting initial response...", style="dim italic"))
            return Group(*elements)

        # Render each iteration
        for i in sorted(self.iterations.keys()):
            iteration = self.iterations[i]

            iter_elements = []

            # Draft
            if iteration.draft:
                draft_text = (
                    iteration.draft[:300] + "..." if len(iteration.draft) > 300 else iteration.draft
                )
                iter_elements.append(
                    Panel(draft_text, title="[bold]Draft[/bold]", border_style="blue")
                )

            # Critique/Feedback
            if iteration.critique:
                critique_text = (
                    iteration.critique[:200] + "..."
                    if len(iteration.critique) > 200
                    else iteration.critique
                )

                # For refinement, show score
                if isinstance(iteration, RefinementIteration):
                    score_bar = "█" * int(iteration.score * 10) + "░" * (
                        10 - int(iteration.score * 10)
                    )
                    critique_title = (
                        f"[bold]🔍 Critique (Score: {iteration.score:.2f}) [{score_bar}][/bold]"
                    )
                else:
                    critique_title = "[bold]🔍 Critique[/bold]"

                iter_elements.append(
                    Panel(critique_text, title=critique_title, border_style="yellow")
                )

            # Improvement with diff (for ReflectionIteration)
            if isinstance(iteration, ReflectionIteration) and iteration.improvement:
                if i > 1 and (i - 1) in self.iterations:
                    prev = self.iterations[i - 1]
                    prev_text = prev.improvement or prev.draft
                    diff_text = self._compute_diff(prev_text, iteration.improvement)
                else:
                    diff_text = self._compute_diff(iteration.draft, iteration.improvement)

                iter_elements.append(
                    Panel(diff_text, title="[bold]✏️  Refined[/bold]", border_style="green")
                )

            # Wrap iteration
            iter_title = f"📝 Iteration {i}"
            is_complete = self._is_iteration_complete(iteration)

            if isinstance(iteration, RefinementIteration):
                if iteration.is_accepted:
                    iter_title += f" ✅ ACCEPTED (score: {iteration.score:.2f})"
                else:
                    iter_title += f" (score: {iteration.score:.2f})"
            elif isinstance(iteration, ReflectionIteration) and iteration.is_correct:
                iter_title += " ✅ CORRECT"

            elements.append(
                Panel(
                    Group(*iter_elements),
                    title=f"[bold]{iter_title}[/bold]",
                    border_style="green" if is_complete else "white",
                )
            )

        # Summary
        last_iter = self.iterations.get(max(self.iterations.keys())) if self.iterations else None
        if last_iter and self._is_iteration_complete(last_iter):
            if isinstance(last_iter, RefinementIteration):
                summary = f"Iterations: {self._make_iteration_progress()}\nFinal Score: {last_iter.score:.2f} ✅ ACCEPTED"
            else:
                summary = f"Iterations: {self._make_iteration_progress()}\nConvergence: ✅ CORRECT"
            elements.append(Panel(summary, title="[bold]📊 Summary[/bold]", border_style="green"))

        return Group(*elements)
