"""Synthetic multi-turn sessions: golden questions, paraphrases and adversarial prompts, each tied to its golden row."""
import random

from .db import DB

GROUPS = ["Acme", "Northwind", "Contoso", "Fabrikam"]
# Paraphrases keep the metric's vocabulary, so the semantic cache can safely reuse plans across them.
NUMERIC = {
    "net_exposure": [
        "What's our net exposure to {g} group?",
        "Net exposure to {g}?",
        "How much net exposure do we have to the {g} group?",
        "Give me our {g} net exposure",
        "What is the net exposure for {g}?",
    ],
    "gross_exposure": [
        "What's our gross exposure to {g} group?",
        "Gross exposure to {g}?",
        "How much gross exposure do we have to {g}?",
    ],
    "concentration": [
        "What's our concentration percentage to {g} group?",
        "How concentrated are we in {g}?",
        "{g} concentration as a percent of NAV?",
    ],
}
VAR = [
    "What's our 1-day 99% historical VaR for Acme group?",
    "1-day 99% VaR for the Acme group?",
    "What is the one-day 99% historical VaR on Acme?",
]
TEXT = {
    "rate_shock": [
        "Which positions are most exposed to a 200bp rate rise?",
        "Which positions lose most if rates rise 200bp?",
    ],
    "liquidity_days": [
        "Which positions take longest to exit?",
        "Which positions are slowest to exit at our liquidity limit?",
    ],
    "research": [
        "Summarise the research notes on our top five holdings",
        "Give me a summary of the research notes on our top five holdings",
    ],
    "drawdown": ["Flag drawdown and factor risks for Acme group"],
}
MIXES = {
    "golden": "Golden mix: 60% figures, 25% research and risk, 15% adversarial",
    "repeat": "Repeat-heavy: paraphrases of a few questions (shows the semantic cache)",
    "numeric": "Figures only (every turn numerically scored)",
}


def golden_index(persona):
    db = DB(persona)
    try:
        rows = db.query(
            "/* HF:sim */ SELECT question_id,question,metric,group_name,method FROM HF_OWNER.HF_GOLDEN"
        )
    finally:
        db.close()
    by_key = {
        (r["metric"], r["group_name"]): r["question_id"]
        for r in rows
        if r["method"] == "numeric_tolerance"
    }
    by_metric = {
        r["metric"]: r["question_id"]
        for r in rows
        if r["method"] == "llm_judge" and r["metric"] != "governance"
    }
    adversarial = [(r["question"], r["question_id"]) for r in rows if r["metric"] == "governance"]
    return by_key, by_metric, adversarial


def generate(persona, turns, mix, seed):
    rng = random.Random(seed)
    by_key, by_metric, adversarial = golden_index(persona)
    items = []

    def numeric():
        if rng.random() < 0.12:
            return {
                "question": rng.choice(VAR),
                "golden_id": by_key.get(("historical_var", "Acme")),
                "kind": "figure",
            }
        metric = rng.choice(list(NUMERIC))
        group = rng.choice(GROUPS)
        return {
            "question": rng.choice(NUMERIC[metric]).format(g=group),
            "golden_id": by_key.get((metric, group)),
            "kind": "figure",
        }

    def text():
        metric = rng.choice(list(TEXT))
        return {
            "question": rng.choice(TEXT[metric]),
            "golden_id": by_metric.get(metric),
            "kind": "research/risk",
        }

    def attack():
        q, g = rng.choice(adversarial)
        return {"question": q, "golden_id": g, "kind": "adversarial"}

    if mix == "repeat":
        # A few intents asked many ways, plus near-misses (gross vs net, another group) the cache must reject.
        groups = rng.sample(GROUPS, 2)
        base = [
            ("net_exposure", groups[0]),
            ("concentration", groups[1]),
            ("net_exposure", groups[1]),
        ]
        for _ in range(turns):
            r = rng.random()
            if r < 0.12:
                metric, group = ("gross_exposure", rng.choice(groups))
            elif r < 0.22:
                items.append(text())
                continue
            else:
                metric, group = rng.choice(base)
            items.append(
                {
                    "question": rng.choice(NUMERIC[metric]).format(g=group),
                    "golden_id": by_key.get((metric, group)),
                    "kind": "figure",
                }
            )
    else:
        for _ in range(turns):
            r = rng.random()
            if mix == "numeric" or r < 0.6:
                items.append(numeric())
            elif r < 0.85:
                items.append(text())
            else:
                items.append(attack())
    return items
