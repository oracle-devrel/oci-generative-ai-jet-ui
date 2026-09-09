"""Grounding eval — do research answers cite the sources they should?

  ./.venv/bin/python tests/eval_grounding.py [golden.json]

Each golden case is a question whose answer definitely lives in the brain, plus a
substring that must appear among the run's cited sources. Runs the FULL research agent
(tools, web, verification pass), so this is the expensive eval — a few questions, run
before anything demo- or publication-facing, not on every commit.

Golden file: JSON list of {"question", "expect_source_contains"}.
Default: tests/golden_grounding.json (sample data); point it at your own.
Exit 1 if any question answers without citing its expected source.
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "oracle" / "agent"))

import anthropic  # noqa: E402
import db  # noqa: E402
from research_agent import run_research  # noqa: E402


def main(golden_path):
    cases = json.load(open(golden_path))
    client = anthropic.Anthropic()
    conn = db.connect()
    failures = 0
    try:
        for c in cases:
            answer, sources = run_research(client, conn, c["question"])
            want = c["expect_source_contains"].lower()
            hit = any(want in (s or "").lower() for s in sources)
            print(f"{'PASS' if hit else 'FAIL'}  {c['question'][:60]!r}")
            print(f"      expected source ~ {c['expect_source_contains']!r}; "
                  f"cited: {', '.join(sources[:4]) or '(none)'}")
            if not hit:
                failures += 1
    finally:
        conn.close()
    print(f"\n{len(cases) - failures}/{len(cases)} grounded")
    return 1 if failures else 0


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else ROOT / "tests" / "golden_grounding.json"
    sys.exit(main(path))
