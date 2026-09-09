"""Pure tests for the backlog ranking engine (oracle/agent/backlog_core).

No DB, no LLM, no clock — every case fixes `today`, so it's fast and deterministic and
runnable anywhere (unlike test_brain.py, which needs the live brain). This is the eval
that earns the backlog loop its keep: the ranking model is the whole value, so the model
is what's pinned here.

  python tests/test_backlog.py
"""
import datetime
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "oracle" / "agent"))

import backlog_core as core  # noqa: E402

TODAY = datetime.date(2026, 7, 12)
CFG = core.Config()          # defaults


def _it(title, **kw):
    return core.Item(title=title, **kw)


# ---- scoring / ranking --------------------------------------------------------------

def test_hard_deadline_pins_to_top():
    """A deadline inside the window outranks a strategic no-deadline item, no matter the
    strategic weight — deadlines have no flex."""
    items = [_it("Strategic idea", type="idea", strategic=True),
             _it("Deal due soon", type="brand-deal", deadline="2026-07-15")]  # 3 days out
    ranked = core.rank(items, TODAY, CFG)
    assert ranked[0].title == "Deal due soon", [r.title for r in ranked]
    assert ranked[0].tier == 0


def test_invalid_deadline_ranks_like_no_deadline():
    """BACKLOG.md is hand-editable, so a typo'd deadline ("TBD") must not crash rank() —
    it sorts like a no-deadline item (regression: None vs int TypeError on tie-break)."""
    items = [_it("typo deadline", type="idea", deadline="TBD"),
             _it("clean idea", type="idea")]
    ranked = core.rank(items, TODAY, CFG)   # must not raise
    assert [r.title for r in ranked] == ["clean idea", "typo deadline"]


def test_overdue_beats_due_soon():
    items = [_it("Due in 2d", type="obligation", deadline="2026-07-14"),
             _it("Overdue 3d", type="obligation", deadline="2026-07-09")]
    ranked = core.rank(items, TODAY, CFG)
    assert ranked[0].title == "Overdue 3d"


def test_far_deadline_does_not_dominate():
    """A deadline 3 months out must NOT crowd out today's strategic work."""
    items = [_it("Strategic now", type="idea", strategic=True),
             _it("Far obligation", type="obligation", deadline="2026-10-30")]
    ranked = core.rank(items, TODAY, CFG)
    assert ranked[0].title == "Strategic now", [(r.title, r.score) for r in ranked]
    assert all(r.tier == 1 for r in ranked)   # neither is a hard deadline


def test_momentum_beats_fresh_idea():
    items = [_it("New idea", type="idea"),
             _it("Already started", type="in-flight")]
    ranked = core.rank(items, TODAY, CFG)
    assert ranked[0].title == "Already started"


# ---- the forced strategic seat ------------------------------------------------------

def test_forced_strategic_seat_swaps_in():
    """Top-3 by raw score = 3 brand deals with approaching (but not hard) deadlines; the
    strategic item sits 4th. The seat rule must pull it into the Top-3 (the counterweight
    to the brand-deal/momentum reflex). Deadlines are >14d out, so all four are Tier 1 and
    the deals are displaceable."""
    items = [_it("Deal A", type="brand-deal", deadline="2026-08-01"),   # ~20d
             _it("Deal B", type="brand-deal", deadline="2026-08-03"),   # ~22d
             _it("Deal C", type="brand-deal", deadline="2026-08-05"),   # ~24d
             _it("Pillar guide", type="idea", strategic=True)]          # no deadline
    ranked = core.rank(items, TODAY, CFG)
    assert all(it.tier == 1 for it in ranked), [(r.title, r.tier) for r in ranked]
    assert [r.title for r in ranked[:3]] == ["Deal A", "Deal B", "Deal C"], \
        [(r.title, round(r.score, 2)) for r in ranked]
    top, swapped = core.select_top(ranked, CFG)
    assert swapped is True, "strategic seat should have swapped in"
    assert "Pillar guide" in [t.title for t in top], [t.title for t in top]


def test_strategic_seat_not_needed_when_already_present():
    items = [_it("Pillar guide", type="idea", strategic=True),
             _it("Deal A", type="brand-deal"),
             _it("Finish X", type="in-flight"),
             _it("Small idea", type="idea")]
    top, swapped = core.select_top(core.rank(items, TODAY, CFG), CFG)
    assert swapped is False
    assert top[0].title == "Pillar guide"


def test_strategic_seat_never_displaces_hard_deadline():
    """Three hard-deadline items fill the Top-3 and one strategic waits below. Hard
    deadlines are non-negotiable, so NO swap happens."""
    items = [_it("Due 1", type="obligation", deadline="2026-07-13"),
             _it("Due 2", type="obligation", deadline="2026-07-14"),
             _it("Due 3", type="obligation", deadline="2026-07-15"),
             _it("Strategic", type="idea", strategic=True)]
    ranked = core.rank(items, TODAY, CFG)
    top, swapped = core.select_top(ranked, CFG)
    assert swapped is False
    assert all(it.tier == 0 for it in top)
    assert "Strategic" not in [t.title for t in top]


def test_no_strategic_anywhere_leaves_top_untouched():
    items = [_it("A", type="brand-deal"), _it("B", type="in-flight"), _it("C", type="idea")]
    top, swapped = core.select_top(core.rank(items, TODAY, CFG), CFG)
    assert swapped is False and len(top) == 3


# ---- aging: kill or commit ----------------------------------------------------------

def test_aged_item_flagged():
    old = (TODAY - datetime.timedelta(days=30)).isoformat()
    items = [_it("Sitting forever", type="idea", since=old),
             _it("Fresh", type="idea", since=TODAY.isoformat())]
    ranked = core.rank(items, TODAY, CFG)
    top, _ = core.select_top(ranked, CFG)
    aged = core.aged_items(ranked, top, TODAY, CFG)
    titles = [it.title for _, it in aged]
    # "Fresh" is young; "Sitting forever" is 30d old but may also be in top (only 2 items).
    # Force it out of the top by padding the top with higher-priority items:
    items2 = items + [_it("D1", deadline="2026-07-13"), _it("D2", deadline="2026-07-14"),
                      _it("D3", deadline="2026-07-15")]
    ranked2 = core.rank(items2, TODAY, CFG)
    top2, _ = core.select_top(ranked2, CFG)
    aged2 = core.aged_items(ranked2, top2, TODAY, CFG)
    assert "Sitting forever" in [it.title for _, it in aged2], [it.title for _, it in aged2]
    assert "Fresh" not in [it.title for _, it in aged2]


def test_aged_excludes_hard_deadline_items():
    old = (TODAY - datetime.timedelta(days=40)).isoformat()
    items = [_it("Old but due", type="obligation", since=old, deadline="2026-07-15"),
             _it("F1", deadline="2026-07-13"), _it("F2", deadline="2026-07-14"),
             _it("F3", deadline="2026-07-16")]
    ranked = core.rank(items, TODAY, CFG)
    top, _ = core.select_top(ranked, CFG)
    aged = core.aged_items(ranked, top, TODAY, CFG)
    assert "Old but due" not in [it.title for _, it in aged]  # a deadline is never 'stale'


# ---- markdown round-trip ------------------------------------------------------------

def test_line_round_trip():
    it = _it("A tricky: title", type="brand-deal", strategic=True, deadline="2026-08-01",
             effort="M", since="2026-07-01", next_action="ship the thing")
    back = core.line_to_item(core.item_to_line(it))
    for f in ("title", "type", "strategic", "deadline", "effort", "since", "next_action", "done"):
        assert getattr(back, f) == getattr(it, f), (f, getattr(back, f), getattr(it, f))


def test_done_marker_round_trips():
    it = _it("Shipped it", type="idea", done=True, since="2026-06-01")
    line = core.item_to_line(it)
    assert line.startswith("- [x]")
    assert core.line_to_item(line).done is True


def test_parse_only_reads_items_section():
    text = ("# Title\n- [ ] **Not an item, before section** · type:idea\n\n"
            "## ▶ This week — Top 3\n1. **Derived view, ignore me**\n\n"
            "## Items\n"
            "- [ ] **Real one** · type:in-flight · strategic:no · deadline:- · effort:- "
            "· since:2026-07-01 · next:do it\n"
            "- [x] **Done one** · type:idea · strategic:no · deadline:- · effort:- "
            "· since:2026-06-01 · next:\n"
            "\n## Later section\n- [ ] **After items, ignore** · type:idea\n")
    items = core.parse_items(text)
    assert [it.title for it in items] == ["Real one", "Done one"], [it.title for it in items]
    assert items[0].type == "in-flight" and items[0].next_action == "do it"
    assert items[1].done is True


def test_render_file_is_reparseable():
    """The full file the agent writes must parse back to the same items — the round-trip
    that keeps the source of truth stable across reviews."""
    items = [_it("Finish video", type="in-flight", strategic=True, since="2026-07-01",
                 next_action="record demo"),
             _it("Guide", type="idea", strategic=True, since="2026-07-05", effort="L"),
             _it("Deal", type="brand-deal", deadline="2026-07-20", since="2026-07-10"),
             _it("Old shipped", type="idea", done=True, since="2026-06-01")]
    rendered = core.render_file(items, TODAY, CFG)
    reparsed = core.parse_items(rendered)
    assert {it.title for it in reparsed} == {it.title for it in items}
    assert core.render_file(reparsed, TODAY, CFG) == rendered   # idempotent


def test_render_digest_smoke():
    items = [_it("Finish video", type="in-flight", strategic=True, since="2026-07-01"),
             _it("Deal due", type="brand-deal", deadline="2026-07-14", since="2026-07-10")]
    d = core.render_digest(items, TODAY, CFG)
    assert "Top 3" in d and "Deal due" in d


# ---- slack drain: pure message filtering --------------------------------------------

def test_slack_human_messages_filters_and_orders():
    import slack_api
    raw = [
        {"type": "message", "text": "third", "ts": "1002.0"},
        {"type": "message", "subtype": "channel_join", "text": "joined", "ts": "1001.5"},
        {"type": "message", "bot_id": "B1", "text": "the bot's own post", "ts": "1001.4"},
        {"type": "message", "text": "  ", "ts": "1001.3"},          # blank -> dropped
        {"type": "message", "text": "first", "ts": "1000.0"},
        {"type": "message", "text": "second", "ts": "1001.0"},
        {"not": "a message"},
    ]
    got = slack_api.human_messages(raw)
    assert [m["text"] for m in got] == ["first", "second", "third"]   # chronological, humans only
    assert all(set(m) == {"ts", "text"} for m in got)


def test_slack_not_configured_is_false(monkeypatch=None):
    import os
    import slack_api
    old = os.environ.pop("SLACK_BOT_TOKEN", None)
    try:
        assert slack_api.configured() is False
    finally:
        if old is not None:
            os.environ["SLACK_BOT_TOKEN"] = old


def test_telegram_parse_updates_filters_and_orders():
    import telegram_api
    raw = [
        {"update_id": 12, "message": {"chat": {"id": 111}, "date": 3, "text": "third"}},
        {"update_id": 10, "message": {"chat": {"id": 111}, "date": 1, "text": "first"}},
        {"update_id": 11, "message": {"chat": {"id": 999}, "date": 2, "text": "stranger"}},
        {"update_id": 13, "message": {"chat": {"id": 111}, "date": 4}},          # no text
        {"update_id": 14, "message": {"chat": {"id": 111}, "date": 5, "text": "  "}},  # blank
        {"update_id": 15, "edited_message": {"chat": {"id": 111}, "date": 6, "text": "edited"}},
    ]
    got = telegram_api.parse_updates(raw, allow_chat_id="111")
    assert [m["text"] for m in got] == ["first", "third", "edited"]   # ordered by update_id, mine only
    assert "stranger" not in [m["text"] for m in got]                 # foreign chat dropped
    # no allowlist -> the stranger is kept (still no blanks / textless)
    allall = telegram_api.parse_updates(raw, allow_chat_id=None)
    assert "stranger" in [m["text"] for m in allall]


if __name__ == "__main__":
    tests = [(n, f) for n, f in sorted(globals().items())
             if n.startswith("test_") and callable(f)]
    passed = failed = 0
    for n, f in tests:
        try:
            f()
            print(f"  PASS  {n}")
            passed += 1
        except Exception as e:
            msg = (str(e).splitlines() or [e.__class__.__name__])[0] or e.__class__.__name__
            print(f"  FAIL  {n}: {msg}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)
