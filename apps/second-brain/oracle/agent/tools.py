"""The agent's one tool: publish a hook and get an engagement score back.

The score follows a FIXED latent rubric. The agent doesn't know the rubric — it
discovers it over time from its own memory of past outcomes. That's the honest
version of "self-improving": run 2 beats run 1 because the agent recalled what
worked, not because we told it the answer.
"""


def score_hook(hook: str) -> float:
    """Latent engagement rubric (deterministic, so the demo is reproducible)."""
    s = 0.30
    if any(c.isdigit() for c in hook):   # a concrete number
        s += 0.25
    if "?" in hook:                       # asks a question
        s += 0.20
    if "you" in hook.lower():             # speaks to the reader
        s += 0.15
    if len(hook) <= 80:                   # punchy, not bloated
        s += 0.10
    return round(min(s, 1.0), 3)


def lesson_for(hook: str, score: float) -> str:
    """A human-readable note describing the hook's features — stored in memory so
    future recall teaches the agent the rubric."""
    feats = [
        "has a number" if any(c.isdigit() for c in hook) else "no number",
        "is a question" if "?" in hook else "not a question",
        "addresses 'you'" if "you" in hook.lower() else "no direct address",
        "punchy (<=80 chars)" if len(hook) <= 80 else f"long ({len(hook)} chars)",
    ]
    return f"scored {score}: " + ", ".join(feats)
