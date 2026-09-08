#!/usr/bin/env python3
"""Showcase a new workshop use case: an AI match-intelligence briefing.

The briefing reuses the same soccer analytics agent stack attendees build in the
workshop: Oracle match data, 92-feature live inference, OracleVS hybrid
retrieval, semantic-only memory, and Grok via OCI GenAI bearer-token auth from
`.env`.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

REPO = Path(__file__).resolve().parent.parent


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--home", default="Spain", help="Home/team A name")
    parser.add_argument("--away", default="Brazil", help="Away/team B name")
    parser.add_argument(
        "--focus",
        default="broadcast",
        help="Briefing audience: broadcast, coach, sponsor, executive, etc.",
    )
    parser.add_argument(
        "--home-advantage",
        action="store_true",
        help="Treat the match as non-neutral; default is neutral venue.",
    )
    parser.add_argument(
        "--no-llm",
        action="store_true",
        help="Skip the final Grok prose rendering and print deterministic JSON only.",
    )
    return parser.parse_args()


def _require_env_for_llm() -> None:
    missing = [
        name for name in ("OCI_GENAI_ENDPOINT", "OCI_GENAI_API_KEY", "OCI_COMPARTMENT_ID", "OCI_GENAI_MODEL_ID")
        if not os.environ.get(name) or "REPLACE_ME" in os.environ.get(name, "")
    ]
    if missing:
        raise RuntimeError(
            ".env is missing required OCI GenAI key(s) for Grok rendering: "
            + ", ".join(missing)
        )


def _validate_briefing(briefing: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    prediction = briefing.get("live_prediction", {})
    if prediction.get("features_used") != 92:
        errors.append(f"expected live_prediction.features_used=92, got {prediction.get('features_used')!r}")
    probs = [
        float(prediction.get("prob_home_win", 0.0) or 0.0),
        float(prediction.get("prob_draw", 0.0) or 0.0),
        float(prediction.get("prob_away_win", 0.0) or 0.0),
    ]
    if max(probs) - min(probs) < 0.05:
        errors.append(f"prediction probabilities look uniform: {probs}")
    if not briefing.get("hybrid_evidence", {}).get("documents"):
        errors.append("hybrid_evidence.documents is empty; run scripts/load_langchain_vectors.py --reset")
    if not briefing.get("semantic_only_baseline", {}).get("facts"):
        errors.append("semantic_only_baseline.facts is empty; run scripts/embed_match_facts.py")
    if not briefing.get("narrative_bullets"):
        errors.append("narrative_bullets is empty")
    return errors


def _render_with_grok(briefing: dict[str, Any]) -> str:
    _require_env_for_llm()
    from soccer_agent.agent.grok_client import chat

    prompt = (
        "Turn this structured soccer analytics briefing into a concise, presenter-ready "
        "match-intelligence script. Include the live probability split, one hybrid "
        "retrieval evidence line, and one semantic-only baseline contrast. Do not invent "
        "numbers.\n\n"
        + json.dumps(briefing, ensure_ascii=False, default=str)[:9000]
    )
    reply = chat(
        [
            {
                "role": "system",
                "content": (
                    "You are a World Cup analytics presenter. Be precise, concise, "
                    "and explicit about which evidence came from the live model, "
                    "OracleVS hybrid retrieval, and semantic-only memory."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        max_tokens=700,
        temperature=0.2,
    )
    return reply.text.strip()


def main() -> int:
    args = _parse_args()
    load_dotenv(REPO / ".env")

    from soccer_agent.agent.tools import dispatch

    briefing = dispatch(
        "build_match_briefing",
        {
            "home_team": args.home,
            "away_team": args.away,
            "neutral": not args.home_advantage,
            "focus": args.focus,
        },
        session_id="match-briefing-showcase",
    )

    errors = _validate_briefing(briefing)
    if errors:
        print("Match briefing validation FAILED:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        print(json.dumps(briefing, indent=2, ensure_ascii=False, default=str))
        return 1

    print("Structured match-intelligence briefing:")
    print(json.dumps(briefing, indent=2, ensure_ascii=False, default=str))

    if not args.no_llm:
        print("\nGrok presenter script (.env OCI_GENAI_API_KEY auth):")
        print(_render_with_grok(briefing))

    print("\nMatch briefing showcase PASSED.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
