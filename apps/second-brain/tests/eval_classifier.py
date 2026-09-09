"""Classifier drift eval — would today's classifier still agree with your verified labels?

  ./.venv/bin/python tests/eval_classifier.py [--n 30]

Your existing `posts.visibility` labels are ground truth (they were reviewed when set).
This samples n labeled chats per class, re-runs the SAME classifier on them, and reports
agreement — run it whenever the rubric, model, or provider changes, BEFORE --apply.

The number that matters most is the DANGEROUS direction: items labeled business/archived
that the new classifier would call 'content' — those would leak into search, the wiki,
and consolidation. Exit code 1 if any appear (the safe direction, content -> private,
merely over-hides and is reported but not fatal).

Costs one small-model LLM call per ~25 items. No writes — read-only against the DB.
"""
import argparse
import pathlib
import random
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "oracle" / "agent"))
sys.path.insert(0, str(ROOT / "scripts"))
import db  # noqa: E402
from classify_private import classify  # noqa: E402  — the SAME rubric/model being shipped


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=30, help="sample size per class")
    ap.add_argument("--seed", type=int, default=26, help="sampling seed (repeatable)")
    args = ap.parse_args()

    conn = db.connect()
    cur = conn.cursor()
    sample = []
    for label in ("content", "business", "archived"):
        cur.execute(
            """SELECT post_id, title, DBMS_LOB.SUBSTR(caption, 220, 1) FROM posts
               WHERE platform_id IN ('claude', 'claude_code', 'chatgpt')
                 AND NVL(visibility, 'content') = :v""", v=label)
        rows = [{"id": int(r[0]), "title": (r[1] or "")[:90],
                 "snip": (str(r[2]) if r[2] else "").replace("\n", " ")[:180],
                 "truth": label} for r in cur.fetchall()]
        random.Random(args.seed).shuffle(rows)
        sample += rows[:args.n]
    conn.close()
    if not sample:
        print("no labeled chats found — load + classify chats first")
        return 0

    print(f"re-classifying {len(sample)} labeled chats...")
    predicted = {}
    for i in range(0, len(sample), 25):
        for r in classify(None, sample[i:i + 25]):
            predicted[int(r["id"])] = r.get("label") or "content"

    agree = 0
    leaks, overhides = [], []
    for s in sample:
        p = predicted.get(s["id"], "content")
        if p == s["truth"]:
            agree += 1
        elif s["truth"] in ("business", "archived") and p == "content":
            leaks.append((s, p))          # DANGEROUS: private would become searchable
        else:
            overhides.append((s, p))      # safe direction: content would be hidden

    print(f"\nagreement: {agree}/{len(sample)} ({100 * agree // len(sample)}%)")
    if leaks:
        print(f"\nDANGEROUS drift — {len(leaks)} private item(s) would flip to content:")
        for s, p in leaks[:10]:
            print(f"  [{s['truth']} -> {p}] {s['title'][:70]}")
    if overhides:
        print(f"\nsafe-direction drift — {len(overhides)} item(s) would be over-hidden:")
        for s, p in overhides[:5]:
            print(f"  [{s['truth']} -> {p}] {s['title'][:70]}")
    if not leaks and not overhides:
        print("no drift.")
    return 1 if leaks else 0


if __name__ == "__main__":
    sys.exit(main())
