"""Load a LinkedIn activity harvest (browser-collected JSON) into the brain.

LinkedIn's data export is unreliable for post content (rich-media posts often arrive
without their text), so the dependable path is harvesting your own activity feed in a
logged-in browser session: scroll /in/<you>/recent-activity/all/, collect each post's
URN, author, text, media type, and relative age, and save as JSON:

  {"harvested_at": "...", "items": [{"urn","actor","header","text","rel","media"}, ...]}

This loader keeps only YOUR original posts (actor match), converts relative ages
("3yr") to approximate dates, and merge-dedupes against existing linkedin rows by
normalized caption prefix — matches get their URL upgraded to the real activity URN,
new posts are inserted. One transaction; --dry to preview.

  ./.venv/bin/python scripts/linkedin_harvest.py [path.json] [--dry]

Config: LINKEDIN_ACTOR (required) — case-insensitive substring of your display name that
identifies your own posts in the harvest.
"""
import json
import os
import pathlib
import re
import sys
from datetime import datetime, timedelta

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "oracle" / "agent"))
import db  # noqa: E402

ACTOR = os.environ.get("LINKEDIN_ACTOR", "").lower()
DEFAULT = pathlib.Path.home() / "Downloads" / "linkedin_harvest.json"

REL = re.compile(r"^(\d+)\s*(h|d|w|mo|yr)$")
UNIT_DAYS = {"h": 0, "d": 1, "w": 7, "mo": 30, "yr": 365}


def rel_to_date(rel):
    """'3yr' -> approximate datetime (published_at is best-effort for harvested posts)."""
    m = REL.match((rel or "").strip().lower())
    if not m:
        return None
    n, unit = int(m.group(1)), m.group(2)
    return datetime.now() - timedelta(days=n * UNIT_DAYS[unit], hours=(1 if unit == "h" else 0) * n)


def norm_cap(s):
    return re.sub(r"\s+", " ", (s or "").strip().lower())[:60]


def main():
    if not ACTOR:
        raise SystemExit("set LINKEDIN_ACTOR to your display name as it appears "
                         "on your posts (used to keep only YOUR originals)")
    args = [a for a in sys.argv[1:] if a != "--dry"]
    dry = "--dry" in sys.argv
    path = pathlib.Path(args[0]) if args else DEFAULT
    data = json.load(open(path))
    mine = [i for i in data["items"]
            if ACTOR in (i.get("actor") or "").lower() and len((i.get("text") or "").strip()) > 20]
    print(f"{len(data['items'])} harvested items, {len(mine)} are original posts with text")

    conn = db.connect()
    cur = conn.cursor()
    cur.execute("alter session disable parallel dml")
    cur.execute("""SELECT post_id, DBMS_LOB.SUBSTR(caption, 300, 1), url
                   FROM posts WHERE platform_id='linkedin'""")
    by_cap = {}
    for pid, cap, url in cur.fetchall():
        by_cap[norm_cap(str(cap or ""))] = (pid, url)

    ins = upd = skip = 0
    try:
        for it in mine:
            url = f"https://www.linkedin.com/feed/update/{it['urn']}/"
            key = norm_cap(it["text"])
            hit = by_cap.get(key)
            if hit:
                pid, old_url = hit
                if old_url != url and "urn:li:activity" not in str(old_url or ""):
                    if not dry:
                        cur.execute("UPDATE posts SET url=:u WHERE post_id=:p", u=url, p=pid)
                    upd += 1
                else:
                    skip += 1
                continue
            when = rel_to_date(it.get("rel"))
            if not dry:
                cur.execute(
                    """INSERT INTO posts (platform_id, kind, title, caption, url, published_at,
                                          visibility, content_embedding)
                       VALUES ('linkedin', :k, :t, :c, :u, :d, 'content',
                               VECTOR_EMBEDDING(MINILM USING :e AS DATA))""",
                    k=("video" if it.get("media") == "video" else "post"),
                    t=it["text"].split("\n")[0][:400],
                    c=it["text"][:8000], u=url, d=when,
                    e=it["text"][:3000])
            by_cap[key] = (None, url)   # a post can appear twice in the harvest (self-repost)
            ins += 1
        if dry:
            conn.rollback()
            print(f"DRY RUN: would insert {ins}, upgrade url on {upd}, skip {skip} already-known")
        else:
            conn.commit()
            print(f"inserted {ins} posts, upgraded url on {upd}, skipped {skip} already-known")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
