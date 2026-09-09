"""Wiki lint — surface review candidates over the compiled wiki. READ-ONLY; never auto-applies.

  python scripts/lint_wiki.py

Reports:
  - overlap/contradiction candidates: page PAIRS close in vector space (may say conflicting or
    duplicate things — worth a human look). Each pair's distance is computed once via a < self-join.
  - orphan pages: no cross-links to/from any other page.
  - ungrounded pages: no citations back to your content.

Technique adapted from mhaviv/karpathy-wiki-26ai's lint.py.
"""
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "oracle" / "agent"))
import db   # noqa: E402

OVERLAP_DIST = 0.20   # cosine distance below this => likely overlap/conflict, review


def main():
    c = db.connect()
    cur = c.cursor()

    print(f"=== overlap / contradiction candidates (cosine distance < {OVERLAP_DIST}) ===")
    cur.execute(
        """
        SELECT a.topic, b.topic,
               ROUND(VECTOR_DISTANCE(a.embedding, b.embedding, COSINE), 3) AS d
        FROM   wiki_pages a
        JOIN   wiki_pages b ON a.page_id < b.page_id
        WHERE  a.embedding IS NOT NULL AND b.embedding IS NOT NULL
          AND  VECTOR_DISTANCE(a.embedding, b.embedding, COSINE) < :t
        ORDER  BY d
        """, t=OVERLAP_DIST)
    rows = cur.fetchall()
    for a, b, d in rows:
        print(f"  [{d}] {a}  ~  {b}")
    print("  (none — pages are well-separated)" if not rows else f"  -> {len(rows)} pair(s) to review")

    print("\n=== orphan pages (no cross-links) ===")
    cur.execute(
        "SELECT topic FROM wiki_pages w WHERE NOT EXISTS "
        "(SELECT 1 FROM page_links l WHERE l.from_page_id = w.page_id OR l.to_page_id = w.page_id) "
        "ORDER BY topic")
    orphans = [r[0] for r in cur.fetchall()]
    print("  (none)" if not orphans else "\n".join(f"  - {t}" for t in orphans))

    print("\n=== ungrounded pages (no citations to your content) ===")
    cur.execute(
        "SELECT topic FROM wiki_pages w WHERE NOT EXISTS "
        "(SELECT 1 FROM page_sources s WHERE s.page_id = w.page_id) ORDER BY topic")
    ungrounded = [r[0] for r in cur.fetchall()]
    print("  (none)" if not ungrounded else "\n".join(f"  - {t}" for t in ungrounded))

    c.close()
    print("\nlint is advisory — nothing was changed.")


if __name__ == "__main__":
    main()
