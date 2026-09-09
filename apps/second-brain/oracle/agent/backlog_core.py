"""Backlog engine — the deterministic core of the prioritization loop.

The problem this solves: ideas and to-dos get *captured* everywhere (Notion, Notes)
but nothing ever forces a re-DECISION, so the list only grows and everything stays
live in your head. This module is the re-decision. It is PURE: no DB, no LLM, no
network, no clock except the `today` you pass in. That's deliberate — the ranking must
be auditable ("why is this #2?") and unit-testable, the same property the health
verdict has. The one place judgment is needed (freeform brain-dump -> typed items) is
an LLM call, and it lives in the private agent, not here.

The ranking model, in one breath:
  1. HARD DEADLINES HAVE NO FLEX. Anything due within CFG.hard_window_days pins to the
     top, ordered by nearness (overdue first). Deadlines beyond the window don't dominate
     — they just lean on the score as they approach.
  2. Below the deadline tier, rank by a transparent blend of STRATEGIC weight (bigger-goal
     work) and MOMENTUM (things already in flight), so neither a whim nor a half-done task
     alone decides order.
  3. FORCED STRATEGIC SEAT. Left alone, a week fills itself with obligations and
     finishing tasks, and the strategic work never moves. So Top-3 selection guarantees at
     least one strategic item a seat (never displacing a hard-deadline item). This is the
     counterweight to that bias, encoded, not hoped for.
  4. AGING = KILL OR COMMIT. An item that sits active and un-promoted past CFG.stale_days
     gets flagged. The graveyard becomes visible instead of silent.

BACKLOG.md is round-tripped here: the `## Items` section is the source of truth (append
or hand-edit there); every other section is a DERIVED VIEW this module regenerates.
"""
from __future__ import annotations

import datetime
import re
from dataclasses import dataclass, field, replace

# Item types. obligation/brand-deal carry a hard edge (someone else is waiting);
# in-flight = momentum (already started); idea = optional, the strategic candidates.
TYPES = ("obligation", "brand-deal", "in-flight", "idea")
EFFORTS = ("S", "M", "L")


@dataclass(frozen=True)
class Config:
    """All the knobs in one place, so the personal layer tunes without touching logic."""
    hard_window_days: int = 14   # deadline within this -> Tier 0 (pins to top, no flex)
    stale_days: int = 21         # active + un-promoted past this -> kill-or-commit flag
    top_n: int = 3               # how many get a seat this week
    w_strategic: float = 3.0     # weight of a bigger-goal item
    w_momentum: float = 2.0      # weight of something already in flight
    w_obligation: float = 1.5    # a deadline-less obligation/brand-deal still leans up
    w_deadline_lean: float = 4.0 # max score lean from a deadline still outside the window
    lean_horizon_days: int = 60  # a deadline farther out than this leans ~nothing yet


CFG = Config()


@dataclass
class Item:
    """One backlog line. Dates are ISO strings or None; `done` items keep for history
    but drop out of the active views."""
    title: str
    type: str = "idea"
    strategic: bool = False
    deadline: str | None = None       # 'YYYY-MM-DD' or None
    effort: str | None = None         # S | M | L | None
    since: str | None = None          # first-seen date, drives aging
    next_action: str = ""
    done: bool = False
    # computed at rank time — never parsed from / written to the file's Items section
    score: float = field(default=0.0, compare=False)
    tier: int = field(default=1, compare=False)      # 0 = hard deadline, 1 = the rest
    reason: str = field(default="", compare=False)


# ---------------------------------------------------------------------------
# dates
# ---------------------------------------------------------------------------

def _parse_date(s: str | None):
    if not s:
        return None
    try:
        return datetime.date.fromisoformat(s.strip())
    except ValueError:
        return None


def days_until(deadline: str | None, today: datetime.date):
    """Days from `today` to the deadline; negative = overdue; None if no valid date."""
    d = _parse_date(deadline)
    return None if d is None else (d - today).days


def age_days(since: str | None, today: datetime.date):
    d = _parse_date(since)
    return None if d is None else max(0, (today - d).days)


# ---------------------------------------------------------------------------
# scoring — deterministic and explainable
# ---------------------------------------------------------------------------

def score_item(it: Item, today: datetime.date, cfg: Config = CFG):
    """Return (tier, score, reason). Pure. Tier 0 = a hard deadline inside the window
    (these sort above everything, by nearness). Tier 1 = ranked by the strategic/momentum
    blend, with a mild lean for a deadline that's approaching but not yet hard."""
    du = days_until(it.deadline, today)
    if du is not None and du <= cfg.hard_window_days:
        # Tier 0. Sort key is nearness: overdue (negative) first. Encode as a big score so
        # it always outranks Tier 1, most-urgent highest.
        reason = f"due in {du}d — hard deadline" if du >= 0 else f"OVERDUE {-du}d"
        return 0, 10_000 - du, reason

    parts = []
    score = 0.0
    if it.strategic:
        score += cfg.w_strategic
        parts.append("strategic")
    if it.type == "in-flight":
        score += cfg.w_momentum
        parts.append("in-flight")
    if it.type in ("obligation", "brand-deal"):
        score += cfg.w_obligation
        parts.append(it.type)
    if du is not None:
        # a deadline outside the hard window leans in as it approaches lean_horizon
        lean = cfg.w_deadline_lean * max(0.0, 1 - du / max(1, cfg.lean_horizon_days))
        if lean > 0:
            score += lean
            parts.append(f"due {du}d")
    return 1, score, ", ".join(parts) or "idea"


def rank(items: list[Item], today: datetime.date, cfg: Config = CFG) -> list[Item]:
    """Score every active item and return a new list ordered best-first. `done` items are
    excluded from the ranking (they live on only in the file's history)."""
    active = [replace(it) for it in items if not it.done]
    for it in active:
        it.tier, it.score, it.reason = score_item(it, today, cfg)
    # tier asc (0 before 1), then score desc, then nearest deadline, then title (stable).
    # days_until returns None for an unparseable hand-edited deadline (e.g. "TBD") —
    # coalesce it to the no-deadline sentinel so one typo can't crash the whole review.
    def _deadline_key(it):
        du = days_until(it.deadline, today) if it.deadline else None
        return du if du is not None else 10**6

    active.sort(key=lambda it: (it.tier, -it.score, _deadline_key(it),
                                it.title.lower()))
    return active


def select_top(ranked: list[Item], cfg: Config = CFG):
    """Pick the week's Top-N from an already-ranked list, GUARANTEEING a strategic seat.

    Returns (top, strategic_seat_swapped: bool). If the natural Top-N already contains a
    strategic item, nothing changes. Otherwise the weakest NON-Tier-0 item in the Top-N is
    swapped for the highest-ranked strategic item below the cut — a hard-deadline item is
    never displaced. If no strategic item exists at all, the natural Top-N stands."""
    top = ranked[:cfg.top_n]
    if any(it.strategic for it in top):
        return top, False
    strategic_below = next((it for it in ranked[cfg.top_n:] if it.strategic), None)
    if strategic_below is None:
        return top, False
    # weakest displaceable = last item in top that isn't a hard-deadline (Tier 0) item
    swap_idx = next((i for i in range(len(top) - 1, -1, -1) if top[i].tier != 0), None)
    if swap_idx is None:            # every seat is a hard deadline — respect that, no swap
        return top, False
    top = list(top)
    top[swap_idx] = strategic_below
    return top, True


def aged_items(ranked: list[Item], top: list[Item], today: datetime.date, cfg: Config = CFG):
    """Active items that have sat past stale_days without earning a Top-N seat and have no
    hard deadline — the 'kill or commit?' pile. Oldest first."""
    seen = {id(it) for it in top}
    out = []
    for it in ranked:
        if id(it) in seen or it.tier == 0:
            continue
        a = age_days(it.since, today)
        if a is not None and a >= cfg.stale_days:
            out.append((a, it))
    out.sort(key=lambda t: -t[0])
    return out


# ---------------------------------------------------------------------------
# markdown round-trip
# ---------------------------------------------------------------------------

_ITEMS_HEADER = "## Items"

# One item per line. The `## Items` section is authoritative; parsing is line-exact so a
# hand-edit round-trips. Grammar:
#   - [ ] **Title** · type:X · strategic:yes|no · deadline:YYYY-MM-DD|- · effort:S|M|L|- · since:YYYY-MM-DD · next:free text
# `- [x]` marks done.
_LINE_RE = re.compile(
    r"^- \[(?P<done>[ xX])\]\s+\*\*(?P<title>.+?)\*\*\s*(?P<rest>·.*)?$")


def _field(rest: str, key: str):
    m = re.search(rf"·\s*{re.escape(key)}:\s*(?P<v>[^·]*)", rest)
    return m.group("v").strip() if m else ""


def line_to_item(line: str) -> Item | None:
    m = _LINE_RE.match(line.rstrip())
    if not m:
        return None
    rest = m.group("rest") or ""
    def clean(v):
        v = v.strip()
        return None if v in ("", "-") else v
    typ = (clean(_field(rest, "type")) or "idea").lower()
    if typ not in TYPES:
        typ = "idea"
    eff = clean(_field(rest, "effort"))
    eff = eff.upper() if eff and eff.upper() in EFFORTS else None
    return Item(
        title=m.group("title").strip(),
        type=typ,
        strategic=_field(rest, "strategic").strip().lower() in ("yes", "y", "true", "1"),
        deadline=clean(_field(rest, "deadline")),
        effort=eff,
        since=clean(_field(rest, "since")),
        next_action=_field(rest, "next").strip(),
        done=m.group("done").lower() == "x",
    )


def item_to_line(it: Item) -> str:
    return (f"- [{'x' if it.done else ' '}] **{it.title}** "
            f"· type:{it.type} "
            f"· strategic:{'yes' if it.strategic else 'no'} "
            f"· deadline:{it.deadline or '-'} "
            f"· effort:{it.effort or '-'} "
            f"· since:{it.since or '-'} "
            f"· next:{it.next_action}".rstrip())


def parse_items(text: str) -> list[Item]:
    """Read every item line under the `## Items` header (order preserved). Lines before that
    header, and non-item lines after it, are ignored — they're prose or derived views."""
    items, in_items = [], False
    for line in text.splitlines():
        if line.strip() == _ITEMS_HEADER:
            in_items = True
            continue
        if in_items and line.startswith("## "):   # a later section ends the Items block
            break
        if in_items:
            it = line_to_item(line)
            if it:
                items.append(it)
    return items


# ---------------------------------------------------------------------------
# rendering — the derived views + the whole file
# ---------------------------------------------------------------------------

def _fmt_meta(it: Item, today: datetime.date):
    bits = []
    du = days_until(it.deadline, today)
    if du is not None:
        bits.append(f"⏰ {'OVERDUE ' + str(-du) + 'd' if du < 0 else 'due ' + str(du) + 'd'}")
    if it.strategic:
        bits.append("⭐ strategic")
    if it.type != "idea":
        bits.append(it.type)
    if it.effort:
        bits.append(f"effort {it.effort}")
    a = age_days(it.since, today)
    if a is not None:
        bits.append(f"{a}d old")
    return " · ".join(bits)


def render_top(top: list[Item], swapped: bool, today: datetime.date):
    lines = ["## ▶ This week — Top 3", ""]
    if not top:
        lines.append("_Nothing active. Add items under `## Items` or run `backlog.py add`._")
        return "\n".join(lines)
    for i, it in enumerate(top, 1):
        tag = "  ⟵ ⭐ protected strategic seat" if (swapped and it.strategic and i == len(top)) else ""
        lines.append(f"{i}. **{it.title}**{tag}")
        meta = _fmt_meta(it, today)
        if meta:
            lines.append(f"   {meta}")
        if it.next_action:
            lines.append(f"   → next: {it.next_action}")
    if swapped:
        lines += ["", "_One seat was reserved for a bigger-goal item so it doesn't get "
                  "starved by deadlines and momentum._"]
    return "\n".join(lines)


def render_kill_commit(aged):
    if not aged:
        return ""
    lines = ["## 🪦 Kill or commit?", "",
             "_Sitting a while with no deadline and no seat. Give it a deadline, make it "
             "strategic, or mark it done to let it go._", ""]
    for a, it in aged:
        lines.append(f"- **{it.title}** — {a}d old, untouched"
                     + (f" · next: {it.next_action}" if it.next_action else ""))
    return "\n".join(lines)


def render_parking(ranked, top, today):
    seen = {id(it) for it in top}
    rest = [it for it in ranked if id(it) not in seen]
    lines = ["## 🅿️ Parking lot", ""]
    if not rest:
        lines.append("_Empty — everything active is in the Top 3._")
        return "\n".join(lines)
    by_type = {t: [] for t in TYPES}
    for it in rest:
        by_type[it.type].append(it)
    labels = {"obligation": "Obligations", "brand-deal": "Brand deals",
              "in-flight": "In flight", "idea": "Ideas"}
    for t in TYPES:
        group = by_type[t]
        if not group:
            continue
        lines.append(f"**{labels[t]}**")
        for it in group:
            meta = _fmt_meta(it, today)
            lines.append(f"- {it.title}" + (f" · {meta}" if meta else ""))
        lines.append("")
    return "\n".join(lines).rstrip()


HEADER = """# Backlog — the one place that owns priority

<!-- Managed by private/agents/backlog.py. The `## Items` section is the source of truth:
     append there, hand-edit freely, or run `backlog.py add "<brain dump>"`. Everything
     above it is a DERIVED VIEW — regenerated every review, don't hand-edit it.
     Financial terms (rates, payment) stay in the Notion tracker / invoicing, NOT here. -->
"""


def render_file(items: list[Item], today: datetime.date, cfg: Config = CFG) -> str:
    """The whole BACKLOG.md: header, the three derived views, then the authoritative
    `## Items` list (active first in ranked order, done items last for history)."""
    ranked = rank(items, today, cfg)
    top, swapped = select_top(ranked, cfg)
    aged = aged_items(ranked, top, today, cfg)

    sections = [HEADER.rstrip(),
                "",
                f"_Last review: {today.isoformat()}_",
                "",
                render_top(top, swapped, today)]
    kc = render_kill_commit(aged)
    if kc:
        sections += ["", kc]
    sections += ["", render_parking(ranked, top, today), "", _ITEMS_HEADER, ""]

    # Items section: active in ranked order (stable, useful), then done items for history.
    ranked_titles = [it.title for it in ranked]
    active = sorted((it for it in items if not it.done),
                    key=lambda it: ranked_titles.index(it.title)
                    if it.title in ranked_titles else 10**6)
    done = [it for it in items if it.done]
    for it in active + done:
        sections.append(item_to_line(it))
    return "\n".join(sections) + "\n"


def render_digest(items: list[Item], today: datetime.date, cfg: Config = CFG) -> str:
    """A standalone snapshot for the weekly report / stdout (no file scaffolding)."""
    ranked = rank(items, today, cfg)
    top, swapped = select_top(ranked, cfg)
    aged = aged_items(ranked, top, today, cfg)
    out = [f"Backlog review — {today.isoformat()}",
           f"({len(ranked)} active · {sum(1 for it in items if it.done)} done)",
           "", render_top(top, swapped, today)]
    kc = render_kill_commit(aged)
    if kc:
        out += ["", kc]
    out += ["", render_parking(ranked, top, today)]
    return "\n".join(out)
