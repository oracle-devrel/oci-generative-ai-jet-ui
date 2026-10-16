"""Camera-friendly terminal rendering shared by both demos (rich)."""

import json

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

console = Console()

BAR_SCALE = 40  # tokens per bar block


def banner(title: str, subtitle: str, color: str):
    console.print()
    console.print(
        Panel(
            Text(title, style=f"bold {color}", justify="center"),
            subtitle=subtitle,
            border_style=color,
            padding=(1, 4),
        )
    )
    console.print()


def turn_header(turn: int, question: str):
    console.print(f"[bold white on grey23] TURN {turn:02d} [/] [bold]{question}[/]")


def token_row(label: str, tokens: int, color: str, extra: str = ""):
    blocks = max(1, tokens // BAR_SCALE)
    bar = "█" * min(blocks, 70) + ("…" if blocks > 70 else "")
    console.print(
        f"   [{color}]{bar}[/] [bold {color}]{tokens:,}[/] tokens  "
        f"[dim]{label}{('  ·  ' + extra) if extra else ''}[/]"
    )


def assistant_reply(text: str):
    short = text.strip().replace("\n", " ")
    if len(short) > 160:
        short = short[:157] + "…"
    console.print(f"   [dim italic]🤖 {short}[/]\n")


def totals(name: str, per_turn: list[int], color: str):
    console.print(
        Panel(
            f"[bold]{name}[/]\n"
            f"tokens on turn 1:  [bold]{per_turn[0]:,}[/]\n"
            f"tokens on turn {len(per_turn)}: [bold {color}]{per_turn[-1]:,}[/]\n"
            f"TOTAL input tokens sent: [bold {color}]{sum(per_turn):,}[/]",
            border_style=color,
            padding=(1, 3),
        )
    )


def save_log(path: str, per_turn: list[int]):
    with open(path, "w") as f:
        json.dump(per_turn, f)
    console.print(f"[dim]log saved → {path}[/]")
