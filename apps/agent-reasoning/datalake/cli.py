"""
CLI for browsing and managing the reasoning datalake.

Provides terminal commands for listing, inspecting, replaying, exporting,
and comparing reasoning sessions stored in Oracle 26ai.

Usage:
    python -m datalake.cli sessions
    python -m datalake.cli show <session_id>
    python -m datalake.cli replay <session_id>
    python -m datalake.cli stats
    python -m datalake.cli export <session_id> --format json
    python -m datalake.cli compare <id1> <id2>
"""

import json
import time

import click
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text

from datalake.config import get_db_config
from datalake.store import ReasoningStore

console = Console()

# Event type color mapping for rich output
EVENT_STYLES = {
    "node": "blue",
    "task": "magenta",
    "sample": "cyan",
    "iteration": "yellow",
    "refinement": "green",
    "pipeline": "bright_magenta",
    "react_step": "red",
    "chain_step": "bright_blue",
    "text": "dim",
    "final": "bold green",
}

STATUS_STYLES = {
    "completed": "green",
    "running": "yellow",
    "failed": "red",
    "cancelled": "dim",
}


def get_store() -> ReasoningStore:
    """Create a ReasoningStore from environment config."""
    return ReasoningStore(get_db_config())


@click.group()
@click.version_option(version="0.1.0", prog_name="datalake")
def cli():
    """Reasoning Datalake CLI - Browse and manage reasoning session traces."""
    pass


# -------------------------------------------------------------------------
# sessions
# -------------------------------------------------------------------------


@cli.command()
@click.option("--strategy", "-s", default=None, help="Filter by strategy")
@click.option("--model", "-m", default=None, help="Filter by model")
@click.option("--status", default=None, help="Filter by status")
@click.option("--limit", "-n", default=20, help="Number of sessions to show")
@click.option("--search", "-q", default=None, help="Search query text")
def sessions(strategy, model, status, limit, search):
    """List recent reasoning sessions."""
    store = get_store()

    try:
        if search:
            results = store.search_sessions(search, limit=limit)
            total = len(results)
        else:
            data = store.list_sessions(strategy=strategy, model=model, status=status, limit=limit)
            results = data["sessions"]
            total = data["total"]

        if not results:
            console.print("[dim]No sessions found.[/dim]")
            return

        table = Table(
            title=f"Reasoning Sessions ({total} total)",
            show_lines=False,
            pad_edge=True,
        )
        table.add_column("ID", style="dim", max_width=10)
        table.add_column("Strategy", style="cyan")
        table.add_column("Model", style="blue")
        table.add_column("Status", justify="center")
        table.add_column("Events", justify="right", style="magenta")
        table.add_column("Query", max_width=50)
        table.add_column("Created", style="dim")

        for s in results:
            status_style = STATUS_STYLES.get(s["status"], "white")
            status_text = Text(s["status"], style=status_style)
            query_preview = (s["query"] or "")[:50]
            if len(s.get("query", "")) > 50:
                query_preview += "..."
            created = s.get("created_at", "")
            if created and len(created) > 19:
                created = created[:19]

            table.add_row(
                s["id"][:8] + "...",
                s["strategy"],
                s["model"],
                status_text,
                str(s.get("event_count", 0)),
                query_preview,
                created,
            )

        console.print(table)

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise click.Abort()


# -------------------------------------------------------------------------
# show
# -------------------------------------------------------------------------


@cli.command()
@click.argument("session_id")
def show(session_id):
    """Show full session detail."""
    store = get_store()

    try:
        session = store.get_session(session_id)
        if session is None:
            console.print(f"[red]Session {session_id} not found.[/red]")
            raise click.Abort()

        # Header panel
        status_style = STATUS_STYLES.get(session["status"], "white")
        header = (
            f"[bold]Session:[/bold] {session['id']}\n"
            f"[bold]Strategy:[/bold] [cyan]{session['strategy']}[/cyan]\n"
            f"[bold]Model:[/bold] [blue]{session['model']}[/blue]\n"
            f"[bold]Status:[/bold] [{status_style}]{session['status']}[/{status_style}]\n"
            f"[bold]Created:[/bold] {session.get('created_at', 'N/A')}\n"
            f"[bold]Completed:[/bold] {session.get('completed_at', 'N/A')}\n"
            f"[bold]Events:[/bold] {session.get('event_count', 0)}\n"
            f"[bold]Tokens:[/bold] {session.get('total_tokens', 'N/A')}"
        )
        console.print(Panel(header, title="Session Detail", border_style="cyan"))

        # Query
        console.print(Panel(session["query"], title="Query", border_style="yellow"))

        # Final answer
        if session.get("final_answer"):
            console.print(
                Panel(
                    session["final_answer"],
                    title="Final Answer",
                    border_style="green",
                )
            )

        # Metrics
        if session.get("metrics"):
            m = session["metrics"]
            metrics_table = Table(title="Performance Metrics", show_lines=True)
            metrics_table.add_column("Metric", style="cyan")
            metrics_table.add_column("Value", justify="right")
            metrics_table.add_row("TTFT", f"{m.get('ttft_ms', 'N/A')} ms")
            metrics_table.add_row("Total Duration", f"{m.get('total_ms', 'N/A')} ms")
            metrics_table.add_row("Tokens/sec", str(m.get("tokens_per_sec", "N/A")))
            metrics_table.add_row("Token Count", str(m.get("token_count", "N/A")))
            console.print(metrics_table)

        # Events summary
        events = session.get("events", [])
        if events:
            console.print(f"\n[bold]Event Timeline[/bold] ({len(events)} events)")
            console.print()

            for evt in events:
                evt_style = EVENT_STYLES.get(evt["event_type"], "white")
                update_tag = " [dim](update)[/dim]" if evt.get("is_update") else ""
                console.print(
                    f"  [{evt_style}]#{evt['sequence_num']:3d} "
                    f"{evt['event_type']:15s}[/{evt_style}]{update_tag}"
                )

            console.print(f"\n[dim]Use 'datalake replay {session_id}' for step-by-step view.[/dim]")

    except click.Abort:
        pass
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise click.Abort()


# -------------------------------------------------------------------------
# replay
# -------------------------------------------------------------------------


@cli.command()
@click.argument("session_id")
@click.option("--delay", "-d", default=0.3, help="Delay between events (seconds)")
@click.option("--no-delay", is_flag=True, help="Show all events immediately")
def replay(session_id, delay, no_delay):
    """Replay reasoning events in terminal with rich formatting."""
    store = get_store()

    try:
        session = store.get_session(session_id)
        if session is None:
            console.print(f"[red]Session {session_id} not found.[/red]")
            raise click.Abort()

        console.print(
            Panel(
                f"[bold]Replaying:[/bold] {session['strategy'].upper()} session\n"
                f"[bold]Query:[/bold] {session['query'][:100]}...\n"
                f"[bold]Model:[/bold] {session['model']}",
                title="Session Replay",
                border_style="cyan",
            )
        )
        console.print()

        events = list(store.replay_session(session_id))
        total = len(events)

        for i, evt in enumerate(events, 1):
            evt_style = EVENT_STYLES.get(evt["event_type"], "white")
            update_marker = " (UPDATE)" if evt.get("is_update") else ""

            # Event header
            header = (
                f"[{evt_style}][bold]Event {i}/{total}[/bold] "
                f"| {evt['event_type'].upper()}{update_marker}[/{evt_style}]"
            )
            console.print(header)

            # Event data
            data = evt.get("data", {})
            if isinstance(data, str):
                try:
                    data = json.loads(data)
                except (json.JSONDecodeError, TypeError):
                    pass

            if isinstance(data, dict):
                # Render key fields based on event type
                _render_event_data(evt["event_type"], data)
            else:
                console.print(f"  {data}")

            console.print()

            if not no_delay and i < total:
                time.sleep(delay)

        # Final answer
        if session.get("final_answer"):
            console.print(
                Panel(
                    session["final_answer"],
                    title="Final Answer",
                    border_style="bold green",
                )
            )

    except click.Abort:
        pass
    except KeyboardInterrupt:
        console.print("\n[dim]Replay interrupted.[/dim]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise click.Abort()


def _render_event_data(event_type: str, data: dict):
    """Render event data with type-specific formatting."""
    if event_type == "chain_step":
        step = data.get("step", "?")
        content = data.get("content", "")
        total = data.get("total_steps", "?")
        icon = data.get("icon", "")
        is_final = data.get("is_final", False)
        tag = " [bold green](FINAL)[/bold green]" if is_final else ""
        console.print(f"  {icon} Step {step}/{total}{tag}")
        if content:
            console.print(f"  [dim]{content[:200]}[/dim]")

    elif event_type == "node":
        node_id = data.get("id", "?")
        depth = data.get("depth", 0)
        score = data.get("score")
        content = data.get("content", "")
        indent = "  " + "  " * depth
        pruned = " [red](PRUNED)[/red]" if data.get("is_pruned") else ""
        best = " [green](BEST)[/green]" if data.get("is_best") else ""
        score_str = f" score={score:.2f}" if score is not None else ""
        console.print(f"{indent}Node {node_id}{score_str}{best}{pruned}")
        if content:
            console.print(f"{indent}[dim]{content[:150]}[/dim]")

    elif event_type == "task":
        task_id = data.get("id", "?")
        desc = data.get("description", "")
        status = data.get("status", "pending")
        progress = data.get("progress", 0)
        console.print(f"  Task {task_id}: {desc[:100]} [{status}] {progress:.0%}")
        if data.get("result"):
            console.print(f"  [dim]Result: {data['result'][:150]}[/dim]")

    elif event_type == "sample":
        sample_id = data.get("id", "?")
        answer = data.get("answer", "")
        votes = data.get("votes", 0)
        winner = " [green](WINNER)[/green]" if data.get("is_winner") else ""
        console.print(f"  Sample {sample_id}: {answer[:80]} (votes={votes}){winner}")

    elif event_type in ("iteration", "refinement"):
        iteration = data.get("iteration", "?")
        score = data.get("score", 0)
        accepted = " [green](ACCEPTED)[/green]" if data.get("is_accepted") else ""
        correct = " [green](CORRECT)[/green]" if data.get("is_correct") else ""
        console.print(f"  Iteration {iteration} (score={score:.2f}){accepted}{correct}")
        if data.get("draft"):
            console.print(f"  [dim]Draft: {data['draft'][:150]}[/dim]")
        if data.get("critique"):
            console.print(f"  [yellow]Critique: {data['critique'][:150]}[/yellow]")

    elif event_type == "pipeline":
        stage = data.get("stage_name", "?")
        stage_idx = data.get("stage_index", 0)
        iteration = data.get("iteration_in_stage", 0)
        score = data.get("score", 0)
        complete = " [green](STAGE COMPLETE)[/green]" if data.get("is_stage_complete") else ""
        pipeline_done = (
            " [bold green](PIPELINE COMPLETE)[/bold green]"
            if data.get("is_pipeline_complete")
            else ""
        )
        console.print(
            f"  Stage {stage_idx}: {stage} / Iteration {iteration} "
            f"(score={score:.2f}){complete}{pipeline_done}"
        )

    elif event_type == "react_step":
        step = data.get("step", "?")
        thought = data.get("thought", "")
        action = data.get("action")
        observation = data.get("observation")
        console.print(f"  Step {step}")
        if thought:
            console.print(f"  [cyan]Thought:[/cyan] {thought[:150]}")
        if action:
            action_input = data.get("action_input", "")
            console.print(f"  [yellow]Action:[/yellow] {action}({action_input[:80]})")
        if observation:
            console.print(f"  [green]Observation:[/green] {observation[:150]}")

    elif event_type == "text":
        text_content = data.get("text", str(data))
        console.print(f"  [dim]{text_content[:200]}[/dim]")

    elif event_type == "final":
        text_content = data.get("text", str(data))
        console.print(f"  [bold green]{text_content[:300]}[/bold green]")

    else:
        # Generic JSON dump for unknown types
        formatted = json.dumps(data, indent=2, default=str)
        if len(formatted) > 500:
            formatted = formatted[:500] + "..."
        console.print(Syntax(formatted, "json", theme="monokai"))


# -------------------------------------------------------------------------
# stats
# -------------------------------------------------------------------------


@cli.command()
def stats():
    """Show aggregate statistics."""
    store = get_store()

    try:
        data = store.get_stats()

        # Summary panel
        summary = (
            f"[bold]Total Sessions:[/bold] {data['total_sessions']}\n"
            f"[bold]Total Events:[/bold] {data['total_events']}\n"
            f"[bold]Completed:[/bold] [green]{data['status_counts']['completed']}[/green]\n"
            f"[bold]Running:[/bold] [yellow]{data['status_counts']['running']}[/yellow]\n"
            f"[bold]Failed:[/bold] [red]{data['status_counts']['failed']}[/red]"
        )
        console.print(Panel(summary, title="Overview", border_style="cyan"))

        # Strategy breakdown
        if data.get("by_strategy"):
            table = Table(title="By Strategy")
            table.add_column("Strategy", style="cyan")
            table.add_column("Sessions", justify="right")
            for strat, count in sorted(data["by_strategy"].items(), key=lambda x: -x[1]):
                table.add_row(strat, str(count))
            console.print(table)

        # Model breakdown
        if data.get("by_model"):
            table = Table(title="By Model")
            table.add_column("Model", style="blue")
            table.add_column("Sessions", justify="right")
            for model, count in sorted(data["by_model"].items(), key=lambda x: -x[1]):
                table.add_row(model, str(count))
            console.print(table)

        # Performance
        perf = data.get("performance", {})
        if any(v is not None for v in perf.values()):
            perf_table = Table(title="Average Performance (Completed Sessions)")
            perf_table.add_column("Metric", style="cyan")
            perf_table.add_column("Value", justify="right")
            perf_table.add_row("Avg TTFT", f"{perf.get('avg_ttft_ms', 'N/A')} ms")
            perf_table.add_row("Avg Duration", f"{perf.get('avg_total_ms', 'N/A')} ms")
            perf_table.add_row("Avg Tokens/sec", str(perf.get("avg_tokens_per_sec", "N/A")))
            perf_table.add_row("Avg Token Count", str(perf.get("avg_token_count", "N/A")))
            console.print(perf_table)

        # Per-strategy performance
        if data.get("strategy_performance"):
            sp_table = Table(title="Performance by Strategy")
            sp_table.add_column("Strategy", style="cyan")
            sp_table.add_column("Sessions", justify="right")
            sp_table.add_column("Avg Duration (ms)", justify="right")
            sp_table.add_column("Avg Tokens/sec", justify="right")
            for sp in sorted(
                data["strategy_performance"], key=lambda x: x.get("avg_duration_ms") or 0
            ):
                sp_table.add_row(
                    sp["strategy"],
                    str(sp["session_count"]),
                    str(sp.get("avg_duration_ms", "N/A")),
                    str(sp.get("avg_tokens_per_sec", "N/A")),
                )
            console.print(sp_table)

        # Event type distribution
        if data.get("by_event_type"):
            table = Table(title="Event Type Distribution")
            table.add_column("Event Type", style="magenta")
            table.add_column("Count", justify="right")
            for etype, count in sorted(data["by_event_type"].items(), key=lambda x: -x[1]):
                table.add_row(etype, str(count))
            console.print(table)

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise click.Abort()


# -------------------------------------------------------------------------
# export
# -------------------------------------------------------------------------


@cli.command()
@click.argument("session_id")
@click.option(
    "--format",
    "-f",
    "fmt",
    type=click.Choice(["json", "md"]),
    default="json",
    help="Export format",
)
@click.option("--output", "-o", default=None, help="Output file path")
def export(session_id, fmt, output):
    """Export a session to JSON or Markdown."""
    store = get_store()

    try:
        if fmt == "json":
            content = store.export_session_json(session_id)
            default_ext = "json"
        else:
            content = store.export_session_markdown(session_id)
            default_ext = "md"

        if content is None:
            console.print(f"[red]Session {session_id} not found.[/red]")
            raise click.Abort()

        if output:
            with open(output, "w") as f:
                f.write(content)
            console.print(f"[green]Exported to {output}[/green]")
        else:
            # Default filename
            filename = f"session_{session_id[:8]}.{default_ext}"
            with open(filename, "w") as f:
                f.write(content)
            console.print(f"[green]Exported to {filename}[/green]")

    except click.Abort:
        pass
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise click.Abort()


# -------------------------------------------------------------------------
# compare
# -------------------------------------------------------------------------


@cli.command()
@click.argument("session_ids", nargs=-1, required=True)
def compare(session_ids):
    """Compare two or more reasoning sessions side by side."""
    if len(session_ids) < 2:
        console.print("[red]At least 2 session IDs required for comparison.[/red]")
        raise click.Abort()

    store = get_store()

    try:
        comparison = store.compare_sessions(list(session_ids))
        sessions = comparison.get("sessions", [])
        summary = comparison.get("summary", {})

        if not sessions:
            console.print("[red]No valid sessions found.[/red]")
            raise click.Abort()

        # Header
        console.print(
            Panel(
                f"[bold]Comparing {len(sessions)} sessions[/bold]\n"
                f"Strategies: {', '.join(summary.get('strategies', []))}\n"
                f"Models: {', '.join(summary.get('models', []))}",
                title="Session Comparison",
                border_style="cyan",
            )
        )

        # Comparison table
        table = Table(title="Side-by-Side Comparison", show_lines=True)
        table.add_column("Field", style="cyan", width=15)
        for s in sessions:
            table.add_column(
                f"{s['strategy']}\n{s['id'][:8]}...",
                max_width=40,
            )

        # Basic fields
        table.add_row("Strategy", *[s["strategy"] for s in sessions])
        table.add_row("Model", *[s["model"] for s in sessions])
        table.add_row(
            "Status",
            *[Text(s["status"], style=STATUS_STYLES.get(s["status"], "white")) for s in sessions],
        )
        table.add_row("Events", *[str(s.get("event_count", 0)) for s in sessions])
        table.add_row("Tokens", *[str(s.get("total_tokens", "N/A")) for s in sessions])

        # Metrics rows
        metrics_fields = [
            ("TTFT (ms)", "ttft_ms"),
            ("Duration (ms)", "total_ms"),
            ("Tokens/sec", "tokens_per_sec"),
            ("Token Count", "token_count"),
        ]
        for label, key in metrics_fields:
            values = []
            for s in sessions:
                m = s.get("metrics") or {}
                val = m.get(key, "N/A")
                if isinstance(val, float):
                    val = f"{val:.2f}"
                values.append(str(val))
            table.add_row(label, *values)

        console.print(table)

        # Query comparison
        queries_same = len(set(s["query"] for s in sessions)) == 1
        if queries_same:
            console.print(
                Panel(sessions[0]["query"][:300], title="Query (same)", border_style="yellow")
            )
        else:
            for s in sessions:
                console.print(
                    Panel(
                        s["query"][:200],
                        title=f"Query ({s['strategy']})",
                        border_style="yellow",
                    )
                )

        # Answer comparison
        console.print("\n[bold]Final Answers:[/bold]")
        for s in sessions:
            answer = s.get("final_answer", "N/A") or "N/A"
            console.print(
                Panel(
                    answer[:500],
                    title=f"{s['strategy']} ({s['id'][:8]})",
                    border_style="green",
                )
            )

    except click.Abort:
        pass
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise click.Abort()


# -------------------------------------------------------------------------
# init-db
# -------------------------------------------------------------------------


@cli.command("init-db")
def init_db():
    """Initialize database tables."""
    store = get_store()
    try:
        store.init_db()
        console.print("[green]Database tables created/verified successfully.[/green]")
    except Exception as e:
        console.print(f"[red]Error creating tables: {e}[/red]")
        raise click.Abort()


# -------------------------------------------------------------------------
# Entry point
# -------------------------------------------------------------------------


def main():
    """CLI entry point."""
    cli()


if __name__ == "__main__":
    main()
