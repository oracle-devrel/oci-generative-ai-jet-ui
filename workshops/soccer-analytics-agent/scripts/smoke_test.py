#!/usr/bin/env python3
"""End-to-end smoke test: hits the live system (Oracle + Grok)."""

from __future__ import annotations

import subprocess
import sys
import uuid
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent


def main() -> int:
    # 1. Run verify.py first — fail fast if the environment isn't ready.
    print("=" * 60)
    print("Stage 1: verify environment")
    print("=" * 60)
    rc = subprocess.call(
        ["uv", "run", "python", str(REPO / "scripts" / "verify.py")], cwd=REPO,
    )
    if rc != 0:
        print("verify.py failed — fix the environment before smoke test.")
        return rc

    # 2. Run one real agent turn against Grok.
    print()
    print("=" * 60)
    print("Stage 2: one real agent turn against Grok")
    print("=" * 60)
    # Import lazily so the env is loaded by verify.py first.
    from soccer_agent.agent.loop import run_turn

    sid = f"smoke-{uuid.uuid4()}"
    reply = run_turn(sid, "Predict Spain vs Brazil at a neutral venue.")
    print(f"Session: {sid}")
    print(f"Reply: {reply.text}")
    print(f"Tools used: {[t['name'] for t in reply.tool_trace]}")

    if not reply.text.strip():
        print("Smoke test FAILED: empty reply.")
        return 1

    predict_trace = next(
        (t for t in reply.tool_trace if t["name"] == "predict_match"),
        None,
    )
    if predict_trace is None:
        print("Smoke test FAILED: predict_match was not used.")
        return 1

    result = predict_trace["result"]
    probs = [
        result.get("prob_home_win", 0.0),
        result.get("prob_draw", 0.0),
        result.get("prob_away_win", 0.0),
    ]
    if result.get("features_used") != 92:
        print(f"Smoke test FAILED: features_used={result.get('features_used')}, expected 92.")
        return 1
    if max(probs) - min(probs) < 0.05:
        print(f"Smoke test FAILED: probabilities look uniform: {probs}")
        return 1

    from soccer_agent.observability.langgraph_steps import list_steps

    steps = list_steps(sid, limit=50)
    event_types = {step.value.get("event_type") for step in steps}
    required_events = {"turn_start", "model_response", "tool_call", "tool_result", "final_response"}
    missing = required_events - event_types
    print(f"LangGraph OracleDB observability steps: {len(steps)} events={sorted(event_types)}")
    if missing:
        print(f"Smoke test FAILED: missing observability events: {sorted(missing)}")
        return 1

    print()
    print("Smoke test PASSED.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
