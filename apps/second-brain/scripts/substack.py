"""Collect step (Substack): your published newsletter/blog posts -> the brain.

Pulls the publication's public archive via Substack's JSON API (no login, no scraping a
logged-in session — this is the same feed readers use), fetches each post's body, chunks
it, and loads everything as kind='article' (kind='episode' for podcast posts). Paid posts
whose body isn't publicly served still land as a row (title/subtitle), just without chunks.

Setup: SUBSTACK_URL=https://<you>.substack.com in oracle/.env (public URL, not a secret).
Run from repo root:  ./.venv/bin/python scripts/substack.py
"""
import datetime
import html.parser
import os
import pathlib

import oracledb
import requests
from dotenv import load_dotenv

ROOT = pathlib.Path(__file__).resolve().parents[1]
load_dotenv(ROOT / "oracle" / ".env")
import sys
sys.path.insert(0, str(ROOT / "oracle" / "agent"))
import db  # noqa: E402  (wallet-aware connect — works for local AND cloud)

oracledb.defaults.fetch_lobs = False
BASE = os.environ.get("SUBSTACK_URL", "").rstrip("/")
if not BASE:
    raise SystemExit("SUBSTACK_URL is not set. Put SUBSTACK_URL=https://<you>.substack.com "
                     "in oracle/.env (see docs/EXPORT_GUIDE.md).")
UA = {"User-Agent": "second-brain-loader (own-content sync)"}


class _Text(html.parser.HTMLParser):
    """body_html -> plain text; block-level tags become paragraph breaks."""
    BLOCK = {"p", "div", "br", "li", "h1", "h2", "h3", "h4", "blockquote", "pre", "tr"}

    def __init__(self):
        super().__init__()
        self.out = []

    def handle_starttag(self, tag, attrs):
        if tag in self.BLOCK:
            self.out.append("\n")

    def handle_data(self, data):
        self.out.append(data)

    def text(self):
        lines = "".join(self.out).splitlines()
        return "\n".join(x.strip() for x in lines if x.strip())


def plain(body_html):
    p = _Text()
    p.feed(body_html or "")
    return p.text()


def iso(s):
    if not s:
        return None
    try:
        return datetime.datetime.fromisoformat(s.replace("Z", "+00:00")).replace(tzinfo=None)
    except Exception:
        return None


def archive():
    """Every post in the publication's public archive, newest first."""
    offset = 0
    while True:
        r = requests.get(f"{BASE}/api/v1/archive", headers=UA, timeout=30,
                         params={"sort": "new", "offset": offset, "limit": 50})
        r.raise_for_status()
        batch = r.json()
        if not batch:
            return
        yield from batch
        offset += len(batch)


def body_of(slug):
    """Full post body (public posts; paid previews come back truncated or empty)."""
    r = requests.get(f"{BASE}/api/v1/posts/{slug}", headers=UA, timeout=30)
    if r.status_code != 200:
        return ""
    return plain(r.json().get("body_html"))


def chunks_of(text, size=1500):
    out, buf = [], ""
    for para in text.split("\n"):
        if buf and len(buf) + len(para) + 1 > size:
            out.append(buf)
            buf = para
        else:
            buf = f"{buf}\n{para}" if buf else para
    if buf.strip():
        out.append(buf)
    return out


def main():
    conn = db.connect()
    cur = conn.cursor()
    cur.execute("alter session disable parallel dml")   # Autonomous DB: allow delete+insert in one txn
    cur.execute("merge into platforms p using (select 'substack' id from dual) s "
                "on (p.platform_id=s.id) when not matched then "
                "insert (platform_id, display_name) values ('substack','Substack')")
    cur.execute("delete from posts where platform_id='substack'")
    # NO commit here: delete + reload is ONE transaction (a mid-run API failure
    # leaves the previous content intact).

    n, total_chunks = 0, 0
    for post in archive():
        title = (post.get("title") or "(untitled)").strip()
        subtitle = (post.get("subtitle") or "").strip()
        url = post.get("canonical_url") or f"{BASE}/p/{post.get('slug', '')}"
        kind = "episode" if post.get("type") == "podcast" else "article"
        body = body_of(post["slug"]) if post.get("slug") else ""
        caption = (subtitle + ("\n\n" + body if body else ""))[:4000] or title
        emb = f"{title}. {subtitle} {body}"[:3000]
        outid = cur.var(oracledb.NUMBER)
        cur.execute(
            """
            insert into posts (platform_id, kind, title, caption, url, published_at,
                               sponsored, visibility, content_embedding)
            values ('substack', :kind, :title, :caption, :url, :pub, 0, 'content',
                    vector_embedding(MINILM using :emb as data))
            returning post_id into :outid
            """,
            kind=kind, title=title[:1000], caption=caption, url=url,
            pub=iso(post.get("post_date")), emb=emb, outid=outid,
        )
        post_id = int(outid.getvalue()[0])
        for i, ch in enumerate(chunks_of(body)):
            cur.execute(
                """insert into content_chunks (post_id, seq, chunk, embedding)
                   values (:pid, :seq, :chunk, vector_embedding(MINILM using :emb as data))""",
                pid=post_id, seq=i, chunk=ch, emb=ch[:3000],
            )
            total_chunks += 1
        n += 1
        if n % 25 == 0:
            print(f"  {n} posts, {total_chunks} chunks...")
    conn.commit()
    print(f"loaded {n} Substack posts + {total_chunks} chunks into the brain")
    conn.close()


if __name__ == "__main__":
    main()
