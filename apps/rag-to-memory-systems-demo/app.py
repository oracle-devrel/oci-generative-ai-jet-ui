"""Interactive CLI for the memory-loop demo. Each turn prints a
structured event log so the loop is observable. Output is colorized via
rich; plain print() is reserved for cases where styling would interfere
(e.g. /sql, which prints raw query text)."""
from __future__ import annotations
import argparse
import asyncio
import decimal
import json
import os
from dotenv import load_dotenv

from pathlib import Path

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.filters import has_completions
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.patch_stdout import patch_stdout

from rich.console import Console
from rich.markdown import Markdown
from rich.padding import Padding
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text

load_dotenv()

# Single shared console. Default word-wrap respects word boundaries; turning
# on soft_wrap here would disable that globally and produce mid-word breaks.
# Use console.print(..., soft_wrap=True) per-call when a specific output
# (e.g. the verbose prompt dump) genuinely shouldn't wrap.
console = Console()

# Width to left-pad multi-line output so wrapped lines align with the
# content column after the [tag] prefix. _tag() pads tags to 10 visible chars
# and we add 1 space, so 11 is the visual content origin.
_INDENT = 11


class _Encoder(json.JSONEncoder):
    """JSON encoder that converts Decimal to int/float."""
    def default(self, o: object) -> object:
        if isinstance(o, decimal.Decimal):
            return int(o) if o == o.to_integral_value() else float(o)
        return super().default(o)


def _dumps(obj: object) -> str:
    return json.dumps(obj, cls=_Encoder)


from memory.db import connect, connect_sync
from memory.ddl import create_all, drop_all
from memory.extraction import extractor_from_env
from memory.agent_session import AgentSession
from memory.manager import MemoryManager
from memory.model import model_from_env
from memory.retrieval import (
    HYBRID_QUERY, VECTOR_ONLY_QUERY, LEXICAL_ONLY_QUERY, LIKE_QUERY,
)
from memory.startup import lexical_available, schema_ready


# Tag → markup color mapping. Tags are the [trace]/[retrieve]/etc. prefixes
# that anchor each line in the turn log; consistent colors per tag make the
# log scannable.
_TAG_STYLE = {
    "trace":    "dim cyan",
    "retrieve": "cyan",
    "assemble": "magenta",
    "model":    "bold green",
    "extract":  "yellow",
    "promote":  "blue",
}

_PROMOTE_STYLE = {
    "written":      "bold green",
    "superseded":   "bold yellow",
    "deduplicated": "blue",
    "rejected":     "red",
}

_TIER_STYLE = {
    "high":     "bold green",
    "standard": "white",
    "low":      "dim",
}


def _tag(name: str) -> str:
    """Render a [tag] prefix in the tag's signature color, with trailing
    whitespace that lines content up at column _INDENT across all tags.

    The visible portion is `[name]` — len(name) + 2 brackets. We pad with
    spaces so visible_width + pad == _INDENT, falling back to at least one
    space if the bracketed name is already that wide or wider. (Without
    the min, tags whose name length matches the indent width would butt
    right against the content — the original bug here.)
    """
    style = _TAG_STYLE.get(name, "white")
    visible_width = len(name) + 2  # brackets
    pad = max(1, _INDENT - visible_width)
    return f"[{style}]\\[{name}][/{style}]" + (" " * pad)


def _styled_tag(name: str) -> Text:
    """Same as _tag() but returns a Text object for use inside Panels/Tables
    where markup strings don't render."""
    style = _TAG_STYLE.get(name, "white")
    t = Text()
    t.append(f"[{name}]", style=style)
    visible_width = len(name) + 2
    t.append(" " * max(1, _INDENT - visible_width))
    return t


HELP = """\
Commands:
  /help                   show this help
  /memory                 dump all current memory state for this tenant/user
  /policies               policies only
  /preferences            preferences only
  /facts                  facts only (active + provisional grouped)
  /episodes               episodes only
  /trace                  last 5 trace events for the current run
  /confirm <fact_id>      flip a provisional fact to active
  /run new                start a new run_id without exiting
  /reset confirm          drop all tables, re-create them, re-seed (irreversible)
  /sql                    print the active unified retrieval query template
  /prompt                 print the assembled prompt text from the last turn
  /verbose [on|off]       toggle full memory + prompt dump per turn
  /quit                   exit
"""


class _RunFlags:
    """Mutable per-session flags toggled by slash commands."""
    def __init__(self, verbose: bool = False):
        self.verbose = verbose


# Slash commands the completer should offer. Sub-dicts give second-level
# completions (e.g. /verbose <Tab> → on/off). None means "no sub-args".
_SLASH_COMMANDS: dict[str, set[str] | None] = {
    "/help": None,
    "/memory": None,
    "/policies": None,
    "/preferences": None,
    "/facts": None,
    "/episodes": None,
    "/trace": None,
    "/confirm": None,        # dynamic fact_id; can't complete usefully here
    "/run": {"new"},
    "/reset": {"confirm"},
    "/sql": None,
    "/prompt": None,
    "/verbose": {"on", "off"},
    "/quit": None,
}

# History persists across runs at this path. Typing the same fact-correction
# message repeatedly during a demo session benefits the most from this.
_HISTORY_PATH = Path.home() / ".cache" / "oracle-memory-system-demo" / "history"


class _SlashCommandCompleter(Completer):
    """Completer that fires only when the buffer starts with '/'.

    Two behaviors stacked:
      1. With no space yet, complete the top-level command. Prefix-matches
         on '/' (so typing just '/' shows every command; typing '/m' narrows
         to commands starting with '/m'). NestedCompleter can't do this on
         its own because its word boundaries don't include '/'.
      2. After the first space, complete the sub-arg for that command if
         the command has known sub-args (e.g. '/verbose ' → on/off).

    Returning no completions for non-slash text keeps the menu silent
    during normal chat even with complete_while_typing=True at the session."""

    def __init__(self, commands: dict[str, set[str] | None]):
        self.commands = commands

    def get_completions(self, document, complete_event):
        text = document.text_before_cursor
        if not text.startswith("/"):
            return

        if " " in text:
            cmd, _, partial = text.partition(" ")
            sub_args = self.commands.get(cmd)
            if sub_args:
                for arg in sorted(sub_args):
                    if arg.startswith(partial):
                        yield Completion(arg, start_position=-len(partial))
            return

        for cmd in self.commands:
            if cmd.startswith(text):
                yield Completion(cmd, start_position=-len(text))


def _build_key_bindings() -> KeyBindings:
    """Custom key bindings layered on top of prompt_toolkit's defaults.

    Escape dismisses the completion menu when it's open. prompt_toolkit's
    default treats Escape as the start of a Meta-key sequence and waits for
    a follow-up keystroke, so a bare Esc never fires; eager=True overrides
    that wait. The has_completions filter scopes the binding so a stray Esc
    elsewhere doesn't break anything."""
    kb = KeyBindings()

    @kb.add("escape", eager=True, filter=has_completions)
    def _dismiss_completion(event):
        event.current_buffer.cancel_completion()

    return kb


def _build_prompt_session() -> PromptSession:
    """A PromptSession with persistent history and slash-command completion.

    complete_while_typing=True at the session level + _SlashCommandCompleter
    gating means: type '/' to auto-pop the menu, keep typing to narrow it,
    no menu for regular chat messages. Escape dismisses an open menu."""
    _HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    return PromptSession(
        history=FileHistory(str(_HISTORY_PATH)),
        completer=_SlashCommandCompleter(_SLASH_COMMANDS),
        complete_while_typing=True,
        key_bindings=_build_key_bindings(),
    )


def _bottom_toolbar(
    model_kind: str, session: AgentSession, min_tier: str,
    flags: _RunFlags,
):
    """Returns a callable prompt_toolkit will re-evaluate on each render, so
    the toolbar reflects mid-session changes like /verbose toggles or /run new."""
    def _render():
        # Use ANSI color tags rich-style, not HTML, because the toolbar is
        # rendered by prompt_toolkit's own renderer.
        return HTML(
            f" <ansicyan>{model_kind}</ansicyan> "
            f"│ tier=<ansiyellow>{min_tier}</ansiyellow> "
            f"│ verbose=<ansigreen>{'on' if flags.verbose else 'off'}</ansigreen> "
            f"│ run=<ansimagenta>{session.run_id}</ansimagenta> "
            f"│ <i>Ctrl-D exit · Ctrl-R search · Tab complete</i>"
        )
    return _render


def _display_name(user_id: str) -> str:
    """Strip the typed scope prefix ('customer:', 'user:', etc.) from a
    user_id for display in chat. Keeps the raw user_id for everything that
    needs the canonical identifier (queries, scope predicates, etc.)."""
    return user_id.split(":", 1)[-1] if ":" in user_id else user_id


def welcome(session: AgentSession) -> None:
    """Agent's opening greeting, printed once at startup after the banner."""
    console.print(
        f"{_tag('model')}Hello [bold]{_display_name(session.user_id)}[/bold]. "
        f"How can I help you today?\n"
    )


def goodbye(session: AgentSession) -> None:
    """Agent's parting line, printed on every exit path so leaving the
    session feels like the assistant signing off rather than a system halt."""
    console.print(
        f"{_tag('model')}Take care, [bold]{_display_name(session.user_id)}[/bold]. "
        f"I'm here if you need help.\n"
    )


def banner(
    session: AgentSession,
    mode: str,
    model_kind: str,
    verbose: bool = False,
    min_tier: str = "low",
) -> None:
    body = Table.grid(padding=(0, 1))
    body.add_column(style="dim", justify="right")
    body.add_column()

    def _onoff(b: bool) -> Text:
        return Text("on", style="bold green") if b else Text("off", style="dim")

    body.add_row("tenant",    Text(session.tenant_id, style="cyan"))
    body.add_row("customer",  Text(session.user_id, style="cyan"))
    body.add_row("agent",     Text(session.agent_id, style="cyan"))
    body.add_row("run",       Text(session.run_id, style="magenta"))
    body.add_row("model",     Text(model_kind, style="bold"))
    body.add_row("retrieval", Text(mode, style="yellow"))
    body.add_row("min tier",  Text(min_tier, style=_TIER_STYLE.get(min_tier, "white")))
    body.add_row("verbose",   _onoff(verbose))

    console.print(Panel(body, title="[bold]memory-loop demo[/bold]",
                        subtitle="[dim]type a message, or /help[/dim]",
                        border_style="cyan", padding=(0, 2)))


_STATUS_STYLE = {
    "active":      ("✓", "bold green"),
    "provisional": ("?", "yellow"),
    "revoked":     ("✗", "red"),
}


async def _dump_facts(manager: MemoryManager, session: AgentSession) -> None:
    """Print active and provisional facts for the tenant as a rich Table.

    Includes the subject column so subject-mismatch bugs (which break
    contradiction → supersession routing) are visible in the dump."""
    cur = manager.conn.cursor()
    await cur.execute(
        "SELECT fact_id, subject, predicate, content, confidence, status "
        "FROM fact_memory WHERE tenant_id = :tid AND superseded_by IS NULL "
        "ORDER BY status, predicate",
        tid=session.tenant_id,
    )
    facts = []
    async for fid, subj, pred, content, conf, status in cur:
        if content is not None and hasattr(content, "read"):
            text = await content.read()
        else:
            text = content
        facts.append({"id": fid, "subject": subj, "predicate": pred,
                      "content": text, "confidence": conf, "status": status})

    table = Table(
        title=f"facts ({len(facts)})", title_style="bold", title_justify="left",
        header_style="bold cyan", border_style="dim",
        show_lines=False, expand=False,
    )
    table.add_column("", width=1)
    table.add_column("id", style="dim", no_wrap=True)
    table.add_column("subject", style="dim")
    table.add_column("predicate", style="yellow")
    table.add_column("content", overflow="fold")
    table.add_column("conf", justify="right", style="dim")
    table.add_column("status", style="dim")
    for f in facts:
        marker, style = _STATUS_STYLE.get(f["status"], ("·", "white"))
        table.add_row(
            Text(marker, style=style),
            f["id"],
            f["subject"] or "",
            f["predicate"] or "",
            f["content"] or "",
            f"{f['confidence']}",
            Text(f["status"], style=style),
        )
    console.print(table)


async def _dump_episodes(manager: MemoryManager, session: AgentSession) -> None:
    """Print active episodes for the tenant as a rich Table."""
    cur = manager.conn.cursor()
    await cur.execute(
        "SELECT episode_id, task_type, title, outcome FROM episodic_memory "
        "WHERE tenant_id = :tid AND status = 'active' "
        "ORDER BY completed_at DESC FETCH FIRST 5 ROWS ONLY",
        tid=session.tenant_id,
    )
    eps = [(r[0], r[1], r[2], r[3]) async for r in cur]
    table = Table(
        title=f"episodes ({len(eps)})", title_style="bold", title_justify="left",
        header_style="bold cyan", border_style="dim", expand=False,
    )
    table.add_column("task_type", style="yellow")
    table.add_column("title", overflow="fold")
    table.add_column("outcome", style="green")
    for _eid, ttype, title, outcome in eps:
        table.add_row(ttype, title, outcome)
    console.print(table)


async def dump_memory(manager: MemoryManager, session: AgentSession) -> None:
    policies = await manager.policy.list_for_tenant(session.tenant_id)
    prefs = await manager.preference.list_for_user(session.user_id, session.tenant_id)

    pol_table = Table(
        title=f"policies ({len(policies)})", title_style="bold", title_justify="left",
        header_style="bold cyan", border_style="dim", expand=False,
    )
    pol_table.add_column("key", style="yellow")
    pol_table.add_column("value")
    for p in policies:
        pol_table.add_row(p["key"], _dumps(p["value"]))
    console.print(pol_table)

    pref_table = Table(
        title=f"preferences ({len(prefs)})", title_style="bold", title_justify="left",
        header_style="bold cyan", border_style="dim", expand=False,
    )
    pref_table.add_column("key", style="yellow")
    pref_table.add_column("value")
    pref_table.add_column("source", style="dim")
    pref_table.add_column("conf", justify="right", style="dim")
    for p in prefs:
        pref_table.add_row(p["key"], _dumps(p["value"]), p.get("source") or "",
                           str(p.get("confidence", "")))
    console.print(pref_table)

    await _dump_facts(manager, session)
    await _dump_episodes(manager, session)


async def handle_command(
    line: str, manager: MemoryManager, session: AgentSession, flags: _RunFlags
) -> bool:
    """Returns False if the loop should exit."""
    parts = line.strip().split(maxsplit=1)
    cmd = parts[0]
    arg = parts[1] if len(parts) > 1 else None

    if cmd == "/help":
        console.print(Panel(HELP.strip(), title="[bold]commands[/bold]",
                            border_style="dim", padding=(0, 2)))
    elif cmd == "/memory":
        await dump_memory(manager, session)
    elif cmd == "/policies":
        for p in await manager.policy.list_for_tenant(session.tenant_id):
            console.print(f"  · [yellow]{p['key']}[/yellow]={_dumps(p['value'])}")
    elif cmd == "/preferences":
        for p in await manager.preference.list_for_user(session.user_id, session.tenant_id):
            console.print(f"  · [yellow]{p['key']}[/yellow]={_dumps(p['value'])}")
    elif cmd == "/facts":
        await _dump_facts(manager, session)
    elif cmd == "/episodes":
        await _dump_episodes(manager, session)
    elif cmd == "/trace":
        for e in (await manager.trace.get_run(session.run_id))[-5:]:
            console.print(
                f"  [dim]t{e['turn_index']}[/dim] "
                f"[yellow]{e['event_type']}[/yellow]: "
                f"{_dumps(e['payload'])[:100]}"
            )
    elif cmd == "/confirm" and arg:
        ok = await manager.fact.confirm(arg)
        if ok:
            console.print(f"  [green]confirmed fact[/green] [dim]{arg}[/dim]")
        else:
            console.print(
                f"  [yellow]no provisional fact with id[/yellow] [dim]{arg}[/dim]"
                f" — already active, revoked, or unknown id"
            )
    elif cmd == "/run":
        if arg == "new":
            session.new_run()
            console.print(f"  new run: [magenta]{session.run_id}[/magenta]")
        else:
            console.print("  [yellow]usage:[/yellow] /run new")
    elif cmd == "/reset":
        if arg != "confirm":
            console.print(
                "  [yellow]/reset[/yellow] will [bold red]drop every demo table[/bold red] "
                "and re-seed the tenant. This is irreversible."
            )
            console.print(
                "  Type [cyan]/reset confirm[/cyan] to proceed, "
                "or anything else to cancel."
            )
            return True

        # DDL needs a sync connection; the async chat conn keeps running.
        console.print("  [dim]dropping tables…[/dim]")
        try:
            sync_conn = connect_sync()
            try:
                drop_all(sync_conn)
                create_all(sync_conn)
            finally:
                sync_conn.close()
        except Exception as e:
            console.print(f"  [red]DDL failed:[/red] {e}")
            return True

        console.print("  [dim]re-seeding demo tenant…[/dim]")
        try:
            # Imported lazily so a missing data/ package (e.g. running app.py
            # outside the project root) doesn't break startup; only /reset
            # depends on it.
            import data.seed as _seed
            await _seed.seed()
        except Exception as e:
            console.print(f"  [red]seed failed:[/red] {e}")
            return True

        # The trace table was dropped too, so the current run_id no longer
        # has any history. Start a clean run so new turns trace from t0.
        session.new_run()
        console.print(
            f"  [green]✓ reset complete[/green] · "
            f"new run: [magenta]{session.run_id}[/magenta]"
        )
    elif cmd == "/sql":
        # Show whichever tier the manager would enter the cascade at.
        # If retrieval has actually degraded on a recent turn, the
        # /prompt panel reflects that via last_context.retrieval_mode.
        tier_sql = {
            "hybrid": HYBRID_QUERY,
            "vector": VECTOR_ONLY_QUERY,
            "lexical": LEXICAL_ONLY_QUERY,
            "like": LIKE_QUERY,
        }
        query = tier_sql.get(manager.retrieval_mode, HYBRID_QUERY)
        console.print(Panel(
            Syntax(query, "sql", theme="monokai", line_numbers=False,
                   word_wrap=True),
            title=f"[bold]active retrieval query · {manager.retrieval_mode}[/bold]",
            border_style="cyan",
        ))
    elif cmd == "/prompt":
        if manager.last_context is None:
            console.print(
                "  [yellow]no prompt yet[/yellow] — "
                "[dim]run a turn first, then /prompt to inspect what the model saw.[/dim]"
            )
        else:
            # The prompt is structured text with <tags> and indentation. Show
            # it inside a Panel for visual separation; wrap in Text() so
            # square-bracket substrings inside the prompt aren't parsed as
            # rich markup tags.
            console.print(Panel(
                Text(manager.last_context.to_prompt_text()),
                title="[bold]last assembled prompt[/bold]",
                subtitle=f"[dim]{manager.last_context.token_estimate()} tokens · "
                         f"retrieval={manager.last_context.retrieval_mode}[/dim]",
                border_style="magenta",
                padding=(0, 1),
            ))
    elif cmd == "/verbose":
        if arg in ("on", "true", "1", None) and arg != "off":
            flags.verbose = True if arg is None else arg in ("on", "true", "1")
        elif arg in ("off", "false", "0"):
            flags.verbose = False
        else:
            console.print("  [yellow]usage:[/yellow] /verbose [on|off]")
            return True
        state = "[bold green]on[/bold green]" if flags.verbose else "[dim]off[/dim]"
        console.print(f"  verbose: {state}")
    elif cmd == "/quit":
        goodbye(session)
        return False
    else:
        console.print("  [red]unknown command.[/red] [dim]/help for the list.[/dim]")
    return True


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Interactive CLI for the memory-loop demo."
    )
    parser.add_argument(
        "--simulated",
        action="store_true",
        help="Force SimulatedModel + RuleBasedExtractor even when "
             "OPENAI_API_KEY is set (sets FORCE_SIMULATED=1).",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Per turn, dump every retrieved memory item and the full "
             "assembled prompt text sent to the model.",
    )
    parser.add_argument(
        "--min-relevance",
        choices=("low", "standard", "high"),
        default=None,
        help="Drop fact/episode hits below this relevance tier in the "
             "assembled prompt. Defaults to MEMORY_MIN_RELEVANCE env var, "
             "or 'low' (no filtering).",
    )
    return parser.parse_args()


def _truncate(text: str, n: int = 120) -> str:
    text = text.replace("\n", " ").strip()
    return text if len(text) <= n else text[: n - 1] + "…"


def _print_verbose_context(context) -> None:
    """Dump every retrieved memory item that landed in the assembled context.
    Called only when --verbose is set. The literal system prompt text used
    to print here too, but it was noisy and rarely the thing being debugged —
    the memories themselves are the high-signal part."""
    pad = "           "  # matches the [tag] prefix width

    def _tier_tag(tier: str) -> str:
        style = _TIER_STYLE.get(tier, "white")
        return f"[{style}]\\[{tier}][/{style}]"

    if context.policies:
        console.print(f"{pad}[bold cyan]policies[/] ({len(context.policies)}):")
        for p in context.policies:
            console.print(
                f"{pad}  - [yellow]{p['policy_key']}[/] = "
                f"{_dumps(p['policy_value'])}"
            )
    if context.preferences:
        console.print(f"{pad}[bold cyan]preferences[/] ({len(context.preferences)}):")
        for p in context.preferences:
            console.print(
                f"{pad}  - [yellow]{p['pref_key']}[/] = "
                f"{_dumps(p['pref_value'])} "
                f"[dim](source={p.get('source')}, conf={p.get('confidence')})[/dim]"
            )
    if context.facts:
        console.print(f"{pad}[bold cyan]facts[/] ({len(context.facts)}):")
        for f in context.facts:
            tier = f.get("relevance", "standard")
            console.print(
                f"{pad}  - {_tier_tag(tier)} "
                f"[yellow]\\[{f.get('predicate', '?')}][/yellow] "
                f"{_truncate(f.get('content', ''))} "
                f"[dim](conf={f.get('confidence')})[/dim]"
            )
    if context.episodes:
        console.print(f"{pad}[bold cyan]episodes[/] ({len(context.episodes)}):")
        for e in context.episodes:
            tier = e.get("relevance", "standard")
            console.print(
                f"{pad}  - {_tier_tag(tier)} "
                f"[yellow]\\[{e.get('task_type', '?')}][/yellow] "
                f"{e.get('title', '')}: {_truncate(e.get('summary', ''))}"
            )
    if context.recent:
        console.print(f"{pad}[bold cyan]recent trace events[/] ({len(context.recent)}):")
        for r in context.recent:
            payload = _dumps(r.get("payload", {}))
            console.print(
                f"{pad}  - [dim]t{r.get('turn_index')}[/dim] "
                f"[yellow]{r.get('event_type')}[/yellow]: "
                f"{_truncate(payload, 100)}"
            )


def _print_verbose_candidates(candidates) -> None:
    """Dump the raw output of the extractor before the gate adjudicates it.
    Lets you tell 'extractor produced nothing' apart from 'gate rejected
    everything the extractor produced'."""
    pad = "           "
    for c in candidates:
        if c.memory_type == "fact":
            scope = (
                f"agent={c.agent_id}" if c.agent_id
                else f"user={c.user_id}" if c.user_id
                else "tenant"
            )
            console.print(
                f"{pad}  - [bold]fact[/bold] "
                f"[yellow]\\[{c.predicate or '?'}][/yellow] "
                f"{_truncate(c.content, 100)} "
                f"[dim](subject={c.subject}, conf={c.confidence}, scope={scope})[/dim]"
            )
        elif c.memory_type == "preference":
            console.print(
                f"{pad}  - [bold]preference[/bold] "
                f"[yellow]{c.pref_key}[/yellow]={_dumps(c.pref_value)} "
                f"[dim](source={c.source}, conf={c.confidence})[/dim]"
            )
        else:
            console.print(
                f"{pad}  - {c.memory_type}: {_truncate(c.content, 100)} "
                f"[dim](conf={c.confidence})[/dim]"
            )


async def main() -> None:
    args = _parse_args()
    if args.simulated:
        os.environ["FORCE_SIMULATED"] = "1"
    flags = _RunFlags(verbose=args.verbose)

    conn = await connect()
    # user_id is the raw identifier (no type prefix); the subject for
    # personal facts is built as "customer:<user_id>" at the seed/
    # extractor layer. Strip any stray "customer:" prefix from the env
    # value so the running session matches what the seed writes —
    # otherwise contradiction detection misses on subject mismatches.
    user_id = os.getenv("DEMO_USER_ID", "jane_doe@example.com").removeprefix("customer:")
    session = AgentSession(
        tenant_id=os.getenv("DEMO_TENANT_ID", "acme-support"),
        user_id=user_id,
        agent_id=os.getenv("DEMO_AGENT_ID", "agent:support_v1"),
    )
    schema_ok, missing = await schema_ready(conn)
    if not schema_ok:
        console.print(
            "[red](!)[/red] Demo tables are missing from this schema "
            f"[dim]({', '.join(t.lower() for t in missing)})[/dim]."
        )
        console.print(
            "    Run [cyan]/reset confirm[/cyan] inside the CLI to drop, "
            "re-create, and re-seed, or quit and run "
            "[cyan]python -m memory.ddl setup && python -m data.seed[/cyan]."
        )
    lexical = await lexical_available(conn) if schema_ok else False
    # Pick the starting tier based on the up-front probe. The retrieval
    # cascade will degrade further per-query if vector or lexical also
    # break at runtime — see memory/retrieval.py for the order.
    mode = "hybrid" if lexical else "vector"
    if schema_ok and not lexical:
        console.print(
            "[yellow](!)[/yellow] Oracle Text not available; "
            "starting retrieval at [yellow]vector[/yellow] tier"
        )
    model = model_from_env()
    extractor = extractor_from_env()
    min_tier = args.min_relevance or os.getenv("MEMORY_MIN_RELEVANCE", "low")
    manager = MemoryManager(
        conn, model, extractor,
        retrieval_mode=mode,
        min_relevance_tier=min_tier,
    )

    banner(session, mode, type(model).__name__, verbose=flags.verbose,
           min_tier=min_tier)
    welcome(session)

    prompt_session = _build_prompt_session()
    toolbar = _bottom_toolbar(
        type(model).__name__, session, min_tier, flags,
    )

    try:
        while True:
            try:
                # patch_stdout keeps rich output above the prompt line clean
                # while background tasks (none yet here, but future-proof) print.
                with patch_stdout():
                    line = (await prompt_session.prompt_async(
                        HTML("<ansicyan><b>> </b></ansicyan>"),
                        bottom_toolbar=toolbar,
                    )).strip()
            except (EOFError, KeyboardInterrupt):
                console.print()  # newline so the sign-off doesn't share the prompt line
                goodbye(session)
                break
            if not line:
                continue

            # Guard: bare "exit"/"quit" is almost always a typo for /quit, not
            # a chat message the user intends for the model. Confirm before
            # leaving so an autopilot keystroke doesn't drop the session.
            if line.lower() in ("exit", "quit"):
                try:
                    with patch_stdout():
                        ans = (await prompt_session.prompt_async(
                            HTML("<ansiyellow>Did you mean to quit? [y/N]: </ansiyellow>"),
                            bottom_toolbar=None,
                        )).strip().lower()
                except (EOFError, KeyboardInterrupt):
                    ans = "n"
                if ans in ("y", "yes"):
                    goodbye(session)
                    break
                console.print("[dim]continuing — type /quit when you mean it.[/dim]")
                continue

            if line.startswith("/"):
                cont = await handle_command(line, manager, session, flags)
                if not cont:
                    break
                continue

            # The model call + LLM extraction inside handle_turn can take a
            # few seconds. Show a spinner so the user knows the turn is
            # processing rather than wondering whether anything is happening.
            # rich.Status manages its own live thread and tears down cleanly
            # when the context exits, even on an async await.
            with console.status("[bold green]thinking…[/]", spinner="dots"):
                response, context, promotions = await manager.handle_turn(session, line)
            counts = {
                "policy": len(context.policies),
                "preference": len(context.preferences),
                "fact": len(context.facts),
                "episodic": len(context.episodes),
                "trace": len(context.recent),
            }
            console.print(f"{_tag('trace')}turn user_msg written")
            console.print(
                f"{_tag('retrieve')}1 query · "
                f"[bold]{sum(counts.values())}[/bold] rows: "
                + ", ".join(f"[bold]{n}[/bold] {k}" for k, n in counts.items() if n)
            )
            console.print(
                f"{_tag('assemble')}prompt: "
                f"[bold]{context.token_estimate()}[/bold] tokens"
            )
            if flags.verbose:
                _print_verbose_context(context)
            console.print(f"{_tag('model')}reply:")
            # Render the model's text as markdown so **bold**, lists, and
            # `code` show their styled form, and pad it so wrapped lines
            # stay flush with the [tag] content column.
            console.print(Padding(Markdown(response.text or ""),
                                  (0, 0, 0, _INDENT)))
            n_cands = len(manager.last_candidates)
            n_style = "bold green" if n_cands else "dim"
            # Label the candidate source by what actually produced them.
            # "combined" = OpenAIModel inlined them in the structured-output
            # reply call; "extractor" = the configured extractor ran as a
            # separate step (simulated stack, or bare-confirmation fallback).
            if manager.last_candidates_source == "combined":
                source_label = f"{type(manager.model).__name__} (combined call)"
            else:
                source_label = type(manager.extractor).__name__
            # Surface deterministic confirmation synthesis when it fires —
            # otherwise the LLM extractor looks like magic from the outside.
            if manager.last_synthesized_message is not None:
                console.print(
                    f"{_tag('extract')}[dim]bare-confirmation synthesis →[/dim] "
                    f"{Text(manager.last_synthesized_message)}"
                )
            console.print(
                f"{_tag('extract')}{source_label} produced "
                f"[{n_style}]{n_cands}[/{n_style}] candidate(s)"
            )
            if flags.verbose and manager.last_candidates:
                _print_verbose_candidates(manager.last_candidates)
            for p in promotions:
                style = _PROMOTE_STYLE.get(p.outcome, "white")
                if p.outcome == "written":
                    console.print(
                        f"{_tag('promote')}[{style}]written[/{style}]: "
                        f"[dim]{p.record_id}[/dim]"
                    )
                elif p.outcome == "deduplicated":
                    console.print(
                        f"{_tag('promote')}[{style}]deduplicated[/{style}]: "
                        f"[dim]matches {p.record_id}[/dim]"
                    )
                elif p.outcome == "rejected":
                    console.print(
                        f"{_tag('promote')}[{style}]rejected[/{style}]: "
                        f"[dim]{p.reason}[/dim]"
                    )
                elif p.outcome == "superseded":
                    console.print(
                        f"{_tag('promote')}[{style}]superseded[/{style}]: "
                        f"[dim]{p.reason}[/dim]"
                    )
            console.print(f"{_tag('trace')}turn model_msg written\n")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
