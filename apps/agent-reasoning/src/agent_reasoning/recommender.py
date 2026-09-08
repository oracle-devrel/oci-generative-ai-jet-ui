"""Query-based strategy recommender.

Analyzes query characteristics (length, keywords, structure) to recommend
the best reasoning strategy without requiring an LLM call. Faster and
cheaper than MetaReasoningAgent for simple routing decisions.
"""

import re
from dataclasses import dataclass


@dataclass
class Recommendation:
    """A strategy recommendation with confidence and reasoning."""

    strategy: str
    confidence: float  # 0.0-1.0
    reason: str


# Keyword patterns mapped to strategies
_STRATEGY_PATTERNS = {
    "cot": {
        "keywords": [
            r"\bstep[- ]by[- ]step\b",
            r"\bexplain\b.*\breasoning\b",
            r"\bshow\b.*\bwork\b",
            r"\bwalk.*through\b",
        ],
        "description": "Step-by-step reasoning for clear logical problems",
    },
    "tot": {
        "keywords": [
            r"\briddle\b",
            r"\bpuzzle\b",
            r"\bmeasure.*gallons?\b",
            r"\bhow many ways\b",
            r"\bcombinations?\b",
            r"\briver crossing\b",
            r"\bjug\b",
        ],
        "description": "Tree exploration for puzzles with branching solutions",
    },
    "react": {
        "keywords": [
            r"\bsearch\b",
            r"\blook up\b",
            r"\bfind\b.*\bcurrent\b",
            r"\bcalculate\b",
            r"\bwho is\b.*\bceo\b",
            r"\bwhat is\b.*\bprice\b",
            r"\bcurrent\b.*\b(?:president|ceo|leader)\b",
        ],
        "description": "Tool use for fact-checking and calculations",
    },
    "reflection": {
        "keywords": [
            r"\bwrite\b.*\b(?:essay|code|poem|story)\b",
            r"\bimprove\b",
            r"\brefine\b",
            r"\breview\b",
            r"\bcritique\b",
            r"\bdraft\b",
        ],
        "description": "Self-reflection for creative/iterative tasks",
    },
    "consistency": {
        "keywords": [
            r"\bopinion\b",
            r"\bcontroversial\b",
            r"\bdebatable\b",
            r"\bmeaning of life\b",
            r"\bphilosoph",
            r"\bethic",
            r"\bshould\b.*\bor\b",
            r"\bbetter\b.*\bor\b",
        ],
        "description": "Multi-sampling for questions with diverse perspectives",
    },
    "decomposed": {
        "keywords": [
            r"\bplan\b",
            r"\bitinerary\b",
            r"\bschedule\b",
            r"\borganize\b",
            r"\bbreak down\b",
            r"\bsteps to\b",
            r"\bhow to build\b",
            r"\bproject plan\b",
        ],
        "description": "Problem decomposition for planning tasks",
    },
    "least_to_most": {
        "keywords": [
            r"\bcomplex\b.*\bproblem\b",
            r"\bmulti[- ]?step\b",
            r"\bphysics\b",
            r"\brelativi",
            r"\bderive\b",
            r"\bprove\b.*\btheorem\b",
        ],
        "description": "Progressive complexity for multi-step problems",
    },
    "refinement": {
        "keywords": [
            r"\bpolish\b",
            r"\bperfect\b",
            r"\bbest possible\b",
            r"\bhigh[- ]quality\b",
            r"\bprofessional\b",
            r"\btechnical writing\b",
        ],
        "description": "Score-based iterative refinement for quality content",
    },
    "debate": {
        "keywords": [
            r"\bpros?\b.*\bcons?\b",
            r"\bargument\b",
            r"\bdebate\b",
            r"\bfor\b.*\bagainst\b",
            r"\bcompare\b.*\bcontrast\b",
            r"\badvantages?\b.*\bdisadvantages?\b",
        ],
        "description": "Adversarial debate for balanced analysis",
    },
    "socratic": {
        "keywords": [
            r"\bwhy\b.*\bwhy\b",
            r"\bunderstand\b.*\bdeeply\b",
            r"\broot cause\b",
            r"\bfirst principles?\b",
            r"\bteach me\b",
            r"\bexplain.*like\b",
        ],
        "description": "Progressive questioning for deep understanding",
    },
    "analogical": {
        "keywords": [
            r"\blike\b.*\banalog",
            r"\bsimilar to\b",
            r"\bmetaphor\b",
            r"\bcompare\b.*\bto\b",
            r"\bhow is\b.*\blike\b",
        ],
        "description": "Analogical reasoning via structural mapping",
    },
    "mcts": {
        "keywords": [
            r"\boptimal\b",
            r"\bbest\b.*\bstrategy\b",
            r"\bgame\b",
            r"\bdecision tree\b",
            r"\bminmax\b",
            r"\bexplore\b.*\boptions?\b",
        ],
        "description": "Monte Carlo tree search for optimization problems",
    },
}


def recommend(query: str, top_k: int = 3) -> list[Recommendation]:
    """Recommend reasoning strategies for a query.

    Analyzes the query text against keyword patterns to suggest
    the most appropriate strategies, ranked by confidence.

    Args:
        query: The user's question/prompt
        top_k: Number of recommendations to return (default 3)

    Returns:
        List of Recommendation objects sorted by confidence (highest first)
    """
    if not query or not query.strip():
        return [Recommendation("standard", 1.0, "Empty or trivial query")]

    query_lower = query.lower()
    scores = []

    for strategy, config in _STRATEGY_PATTERNS.items():
        match_count = 0
        for pattern in config["keywords"]:
            if re.search(pattern, query_lower):
                match_count += 1

        if match_count > 0:
            # Confidence scales with matches, capped at 0.95
            confidence = min(0.95, 0.4 + match_count * 0.2)
            scores.append(
                Recommendation(
                    strategy=strategy,
                    confidence=confidence,
                    reason=config["description"],
                )
            )

    # Sort by confidence descending
    scores.sort(key=lambda r: r.confidence, reverse=True)

    # Always include "standard" as fallback if few matches
    if len(scores) < top_k:
        scores.append(Recommendation("standard", 0.3, "General-purpose direct generation"))

    return scores[:top_k]


def recommend_one(query: str) -> str:
    """Return the single best strategy name for a query."""
    recs = recommend(query, top_k=1)
    return recs[0].strategy if recs else "standard"
