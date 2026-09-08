"""Fabrication probe — does the verification gate still catch planted lies?

  ./.venv/bin/python tests/eval_verify.py

Feeds verify_answer() a synthetic research transcript plus a draft containing BOTH
supported claims and deliberate fabrications, then asserts:
  1. every fabrication is flagged (unsupported/contradicted) and absent from the revision
  2. every true claim survives

Run it whenever the model, the VERIFY_SYSTEM prompt, or the provider changes — an
accuracy gate that silently stopped catching lies is worse than no gate (it launders
fabrications with a 'verified' feel). Costs one LLM call.
"""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "oracle" / "agent"))

import anthropic  # noqa: E402
from research_agent import verify_answer  # noqa: E402

MESSAGES = [
    {"role": "user", "content": "Question about my content: what have I made about vector search?"},
    {"role": "assistant", "content": [{"type": "text", "text": "Searching."}]},
    {"role": "user", "content": [{"type": "text", "text":
        'TOOL RESULT search_content: ['
        '{"title": "AI Vector Search in 90 seconds", "platform": "youtube", "published": "2025-11-02"},'
        '{"title": "Hybrid search: vectors + keywords", "platform": "linkedin"}] '
        'TOOL RESULT get_post: {"title": "AI Vector Search in 90 seconds", "views": 8400, '
        '"published": "2025-11-02"}'}]},
]

TRUE_CLAIMS = [
    ("published 'AI Vector Search in 90 seconds' on YouTube", "90 seconds"),
    ("has 8,400 views", "8,400"),
]
FABRICATIONS = [
    ("it was featured at Oracle CloudWorld's keynote", "CloudWorld"),
    ("you have published 12 vector search videos", "12 vector search videos"),
]

DRAFT = ("You published 'AI Vector Search in 90 seconds' on YouTube in November 2025, which has "
         "8,400 views, and it was featured at Oracle CloudWorld's keynote. Counting related posts, "
         "you have published 12 vector search videos. You also posted 'Hybrid search: vectors + "
         "keywords' on LinkedIn.")


def main():
    revised, claims = verify_answer(anthropic.Anthropic(), MESSAGES, DRAFT)
    verdicts = {c["claim"]: c["verdict"] for c in claims}
    failures = []

    for desc, marker in FABRICATIONS:
        caught = any(marker.lower() in c["claim"].lower() and c["verdict"] != "supported"
                     for c in claims)
        gone = marker.lower() not in revised.lower() or "(unverified)" in revised.lower()
        status = "caught" if caught else "MISSED"
        print(f"fabrication [{status:6s}] {desc}")
        if not (caught and gone):
            failures.append(f"fabrication survived: {desc}")
    for desc, marker in TRUE_CLAIMS:
        kept = marker.lower() in revised.lower()
        print(f"true claim  [{'kept' if kept else 'LOST':6s}] {desc}")
        if not kept:
            failures.append(f"true claim lost: {desc}")

    print(f"\nrevised: {revised[:300]}")
    if failures:
        print("\nFAIL:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("\nPASS: all fabrications caught, all true claims kept")
    return 0


if __name__ == "__main__":
    sys.exit(main())
