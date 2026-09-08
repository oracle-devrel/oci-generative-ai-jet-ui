"""Ingest LinkedIn posts into the brain from a JSON file of {time, text} objects.

LinkedIn has no clean API for your own posts, so this takes posts captured from your activity
page (relative times like '2w', '1mo') or a future export, converts the times to approximate
dates, and loads them as content. Idempotent per post (dedups on a content hash).

  ./.venv/bin/python scripts/linkedin.py ~/Downloads/linkedin_posts.json
"""
import datetime
import hashlib
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "oracle" / "agent"))
import db  # noqa: E402

NOW = datetime.datetime.now()
DOW = ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY", "SUNDAY"]


def to_date(t):
    t = (t or "").strip().upper()
    m = re.match(r"(\d+)\s*(H|D|W|MO|Y)", t)
    if m:
        n, u = int(m.group(1)), m.group(2)
        return NOW - datetime.timedelta(days={"H": 0, "D": n, "W": n * 7, "MO": n * 30, "Y": n * 365}[u])
    if t == "YESTERDAY":
        return NOW - datetime.timedelta(days=1)
    if t in DOW:
        return NOW - datetime.timedelta(days=(NOW.weekday() - DOW.index(t)) % 7 or 7)
    return None


def main():
    if len(sys.argv) < 2:
        sys.exit("usage: linkedin.py /path/to/linkedin_posts.json")
    posts = json.load(open(sys.argv[1]))
    conn = db.connect()
    cur = conn.cursor()
    cur.execute("alter session disable parallel dml")
    cur.execute("merge into platforms p using (select 'linkedin' id from dual) s "
                "on (p.platform_id=s.id) when not matched then "
                "insert (platform_id, display_name) values ('linkedin','LinkedIn')")
    n = skip = 0
    for p in posts:
        text = (p.get("text") or "").strip()
        if len(text) < 25:
            skip += 1
            continue
        h = hashlib.md5(text[:200].encode("utf-8")).hexdigest()[:12]
        url = f"https://www.linkedin.com/feed/update/lh-{h}"
        title = text.split("\n", 1)[0][:150]
        cur.execute("delete from posts where url = :u", u=url)
        cur.execute(
            """insert into posts (platform_id, kind, title, caption, url, published_at,
                   visibility, content_embedding)
               values ('linkedin', 'post', :t, :c, :u, :p, 'content',
                   vector_embedding(MINILM using :e as data))""",
            t=title, c=text[:4000], u=url, p=to_date(p.get("time")),
            e=(title + ". " + text)[:3000])
        n += 1
    conn.commit()
    total = cur.execute("select count(*) from posts where platform_id='linkedin'").fetchone()[0]
    print(f"ingested {n} LinkedIn posts ({skip} skipped); total linkedin now {total}")
    conn.close()


if __name__ == "__main__":
    main()
