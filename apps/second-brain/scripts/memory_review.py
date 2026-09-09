"""Memory hygiene review — the FORGETTING report. Report-only: it never deletes.

  ./.venv/bin/python scripts/memory_review.py            # human-readable report
  ./.venv/bin/python scripts/memory_review.py --json     # machine-readable (for the
                                                          # weekly loop-health note)

A memory store that only grows drifts toward noise: time-bound facts go stale
("preparing the launch" is false a month later), near-duplicates pile up, and every
extra row makes recall a little worse. Mature agent-memory practice (Letta's
sleep-time compute, Mem0's dedup/conflict pipeline, Anthropic's memory curation)
treats FORGETTING as a designed stage of the loop. This is that stage's audit:

  1. STALE-BY-LANGUAGE — old memories written in present/future tense about
     time-bound states (structural regex, no LLM). Old durable facts are fine;
     old "currently working on X" facts are lies with a timestamp.
  2. NEAR-DUPLICATES — memory pairs whose embeddings sit closer than the
     threshold (in-database VECTOR_DISTANCE; custom track only — the OAMP
     package dedupes at extraction time).
  3. VOLUME — per-store counts and growth, so "memory is getting noisy" is a
     number, not a feeling.

Review the report, then retire rows by hand (SQL) or via the package's lifecycle
API. When the same finding shows up run after run, that's the signal to automate
that specific retirement — not before. (Deliberately conservative: deleting
memories is the one loop that should never run unattended first.)
"""
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "oracle" / "agent"))
import oracledb  # noqa: E402

import db  # noqa: E402

oracledb.defaults.fetch_lobs = False

# present/future-tense, time-bound markers: a memory OLDER than STALE_AFTER_DAYS that
# still "speaks in the present" about a temporary state is a staleness candidate.
TEMPORAL = re.compile(
    r"\b(currently|right now|this (week|month|quarter)|next (week|month)|upcoming|"
    r"in progress|is preparing|is planning|is working on|recently|soon|about to|"
    r"not yet|today|tomorrow)\b", re.I)
STALE_AFTER_DAYS = 60
DUP_DISTANCE = 0.15          # cosine distance below this = near-duplicate pair


def is_stale_candidate(text, age_days, stale_after=STALE_AFTER_DAYS):
    """Pure + unit-tested: old enough AND written in time-bound present tense."""
    return age_days >= stale_after and bool(TEMPORAL.search(text or ""))


def review(conn):
    cur = conn.cursor()
    out = {"stale_candidates": [], "duplicate_pairs": [], "counts": {}}

    # --- volume, both stores (whichever exist) ---
    for table, col in (("semantic_memory", "fact"), ("brain_memory", "content")):
        try:
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            out["counts"][table] = cur.fetchone()[0]
        except oracledb.DatabaseError:
            continue   # store not present on this backend/schema

    # --- stale-by-language, both stores ---
    for table, idcol, col, when in (
            ("semantic_memory", "fact_id", "fact", "created_at"),
            ("brain_memory", "rowid", "content", "created_at")):
        if table not in out["counts"]:
            continue
        try:
            cur.execute(f"SELECT {idcol}, {col}, "
                        f"TRUNC(SYSDATE - CAST({when} AS DATE)) FROM {table}")
            for rid, text, age in cur.fetchall():
                if is_stale_candidate(str(text or ""), int(age or 0)):
                    out["stale_candidates"].append(
                        {"store": table, "id": str(rid), "age_days": int(age),
                         "text": str(text)[:180]})
        except oracledb.DatabaseError:
            continue

    # --- near-duplicates (custom store; embeddings are ours to query) ---
    if out["counts"].get("semantic_memory"):
        try:
            cur.execute("""
                SELECT a.fact_id, b.fact_id, a.fact, b.fact,
                       VECTOR_DISTANCE(a.embedding, b.embedding, COSINE) d
                FROM semantic_memory a JOIN semantic_memory b ON a.fact_id < b.fact_id
                WHERE VECTOR_DISTANCE(a.embedding, b.embedding, COSINE) < :thr
                ORDER BY d FETCH FIRST 25 ROWS ONLY""", thr=DUP_DISTANCE)
            for ida, idb, fa, fb, d in cur.fetchall():
                out["duplicate_pairs"].append(
                    {"ids": [int(ida), int(idb)], "distance": round(float(d), 3),
                     "a": str(fa)[:120], "b": str(fb)[:120]})
        except oracledb.DatabaseError:
            pass
    return out


def main():
    conn = db.connect()
    try:
        out = review(conn)
    finally:
        conn.close()
    if "--json" in sys.argv:
        print(json.dumps(out, indent=1))
        return
    print("MEMORY HYGIENE REVIEW (report-only — nothing was deleted)\n")
    print("counts:", ", ".join(f"{k}={v}" for k, v in out["counts"].items()) or "no stores found")
    print(f"\nstale candidates (>= {STALE_AFTER_DAYS}d old, time-bound language): "
          f"{len(out['stale_candidates'])}")
    for s in out["stale_candidates"][:15]:
        print(f"  [{s['store']} {s['id']}] {s['age_days']}d: {s['text']}")
    print(f"\nnear-duplicate pairs (cosine < {DUP_DISTANCE}): {len(out['duplicate_pairs'])}")
    for p in out["duplicate_pairs"][:10]:
        print(f"  d={p['distance']}  #{p['ids'][0]} ~ #{p['ids'][1]}")
        print(f"    a: {p['a']}\n    b: {p['b']}")
    if not out["stale_candidates"] and not out["duplicate_pairs"]:
        print("\nclean — nothing to retire this pass.")


if __name__ == "__main__":
    main()
