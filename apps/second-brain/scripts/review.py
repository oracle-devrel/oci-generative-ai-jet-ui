"""Nightly review (propose-only) — surfaces things to look at; never changes anything.

Standout check: a SECURITY scan that escalates leaked-secret patterns found in ingested content
(defense-in-depth over the redaction done at ingest — catches anything that slipped through, esp.
from AI-chat / Claude Code transcripts). Also flags wiki pages worth review.

  python scripts/review.py

Read-only. Exits non-zero if any secret is found, so a scheduler can alert loudly.
Pattern idea + propose-only/security-escalation framing from mhaviv/brain-scheduled-tasks.
"""
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "oracle" / "agent"))
import db   # noqa: E402

# leaked-credential patterns (Oracle REGEXP-compatible). Scanned in-DB so only matches transfer.
SECRET_PATTERNS = [
    r"sk-ant-[A-Za-z0-9_-]{20,}",        # Anthropic
    r"sk-[A-Za-z0-9_-]{20,}",            # OpenAI classic + sk-proj-... project keys
    r"ntn_[A-Za-z0-9]{20,}",             # Notion
    r"AKIA[0-9A-Z]{16}",                 # AWS access key
    r"gh[pousr]_[A-Za-z0-9]{20,}",       # GitHub token
    r"github_pat_[A-Za-z0-9_]{20,}",     # GitHub fine-grained PAT
    r"xox[baprs]-[A-Za-z0-9-]{10,}",     # Slack
    r"AIza[0-9A-Za-z_-]{30,}",           # Google API key
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
]
SCAN = [("posts", "post_id", "caption", "title"),
        ("content_chunks", "chunk_id", "chunk", "post_id")]


def scan_secrets(conn):
    hits = []
    cur = conn.cursor()
    for table, idcol, textcol, refcol in SCAN:
        for pat in SECRET_PATTERNS:
            cur.execute(
                f"SELECT {idcol}, {refcol}, REGEXP_SUBSTR({textcol}, :p) "
                f"FROM {table} WHERE REGEXP_LIKE({textcol}, :p)", p=pat)
            for rid, ref, match in cur.fetchall():
                m = match or ""
                masked = (m[:6] + "…" + m[-3:]) if len(m) > 12 else "…"
                hits.append((table, rid, ref, masked))
    return hits


def main():
    conn = db.connect()
    print("=== SECURITY: leaked-secret scan over ingested content ===")
    hits = scan_secrets(conn)
    if hits:
        print(f"  ⚠️  {len(hits)} possible secret(s) found — REVIEW + scrub:")
        for table, rid, ref, masked in hits:
            print(f"    [{table} {rid}] ref={ref}  match={masked}")
    else:
        print("  ✅ clean — no secret patterns found in posts/chunks")

    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM wiki_pages w WHERE NOT EXISTS "
                "(SELECT 1 FROM page_sources s WHERE s.page_id = w.page_id)")
    ungrounded = cur.fetchone()[0]
    print(f"\n=== wiki: {ungrounded} ungrounded page(s) (run lint_wiki.py for detail) ===")

    conn.close()
    print("\nreview is propose-only — nothing was changed.")
    sys.exit(2 if hits else 0)


if __name__ == "__main__":
    main()
