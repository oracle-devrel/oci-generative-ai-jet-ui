"""Retrieval eval — golden queries that must keep finding the right thing.

  ./.venv/bin/python tests/eval_retrieval.py [golden.json]

Tests prove the code runs; this proves retrieval QUALITY holds. Each golden case says:
for this query, an item whose title contains this substring must appear in the top k.
Runs entirely in-database (vector + lexical fusion) — no LLM, no API cost — so it's
cheap to run after anything that could shift ranking: loader changes, fusion weight
tuning, chunking changes, embedding model swaps, big imports.

Golden file: JSON list of {"query", "expect_title_contains", "k"} (k defaults to 8).
Negative cases: {"query", "forbid_title_contains", "top"} asserts a known noise item
does NOT appear in the top `top` (defaults to k) — use it to pin down ranking bugs
(e.g. a chunked log that once flooded the fusion) so they can't quietly return.
Default file is tests/golden_retrieval.json (works on the sample data). Point it at
your own golden set once you've loaded your own content — keep one; when you notice
a query that SHOULD find something and doesn't, fix it, then add it here so it can
never quietly regress again.

Exit code 1 on any miss, so it can gate CI or a pre-push hook.
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "oracle" / "agent"))
import db                      # noqa: E402
from content import search_hybrid  # noqa: E402


def run(golden_path):
    cases = json.load(open(golden_path))
    conn = db.connect()
    misses = []
    try:
        for c in cases:
            k = int(c.get("k", 8))
            rows = search_hybrid(conn, c["query"], k)
            titles = [str(r.get("title") or "") for r in rows]
            if "forbid_title_contains" in c:
                # NEGATIVE case: a known noise item must NOT rank in the top `top`.
                # (Born from a real regression: a long chunked build log outscored
                # everything by accumulating one RRF increment per chunk.)
                top = int(c.get("top", k))
                bad = c["forbid_title_contains"].lower()
                hit = next((i for i, t in enumerate(titles[:top], 1) if bad in t.lower()), None)
                status = f"noise@{hit}" if hit else f"clean top {top}"
                print(f"{'FAIL' if hit else 'PASS':4s}  {status:12s}  {c['query'][:58]!r} "
                      f"-> forbid ...{bad[:40]!r}")
                if hit:
                    misses.append(c)
                continue
            want = c["expect_title_contains"].lower()
            hit = next((i for i, t in enumerate(titles, 1) if want in t.lower()), None)
            status = f"rank {hit}/{k}" if hit else f"MISS (top {k})"
            print(f"{'PASS' if hit else 'FAIL':4s}  {status:12s}  {c['query'][:58]!r} "
                  f"-> ...{c['expect_title_contains'][:40]!r}")
            if not hit:
                misses.append(c)
                for i, t in enumerate(titles[:3], 1):
                    print(f"        got {i}: {t[:70]}")
    finally:
        conn.close()
    print(f"\n{len(cases) - len(misses)}/{len(cases)} golden queries passed")
    return 1 if misses else 0


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else ROOT / "tests" / "golden_retrieval.json"
    sys.exit(run(path))
