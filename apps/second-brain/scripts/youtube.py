"""Collect step (YouTube): yt-dlp metadata -> canonical Markdown + Oracle.

Pipeline:
  1. yt-dlp --dump-json  (already run -> exports/youtube/videos.jsonl)
  2. this script: each video -> sources/youtube/<id>.md  (canonical layer)
                              -> a row in Oracle `posts` (Duality model) with an
                                 in-DB embedding for semantic search.

The SAME shape works for every platform — they all land in `posts` — so "collect"
scales from YouTube to Instagram to podcast transcripts without changing the database.

Run from repo root:  ./.venv/bin/python scripts/youtube.py
"""
import datetime
import json
import os
import pathlib
import re

import oracledb
from dotenv import load_dotenv

ROOT = pathlib.Path(__file__).resolve().parents[1]
load_dotenv(ROOT / "oracle" / ".env")
oracledb.defaults.fetch_lobs = False

SRC = ROOT / "sources" / "youtube"
EXPORT_DIR = ROOT / "exports" / "youtube"   # reads every *.jsonl here (videos.jsonl, shorts.jsonl, ...)


def connect():
    # single source of truth: env-driven, wallet-aware, NO password fallback (oracle/agent/db.py)
    import sys
    sys.path.insert(0, str(ROOT / "oracle" / "agent"))
    import db
    return db.connect()


def yyyymmdd(s):
    return datetime.datetime.strptime(s, "%Y%m%d") if s else None


def frontmatter(v):
    fm = {
        "id": f"yt_{v['id']}", "platform": "youtube", "type": "video",
        "url": v.get("webpage_url"), "published": v.get("upload_date"),
        "title": v.get("title"), "views": v.get("view_count"),
        "duration_s": v.get("duration"),
    }
    lines = ["---"]
    for k, val in fm.items():
        lines.append(f"{k}: {json.dumps(val) if isinstance(val, str) else val}")
    lines.append("---\n")
    return "\n".join(lines)


def main():
    SRC.mkdir(parents=True, exist_ok=True)
    # merge every yt-dlp dump in the folder (videos.jsonl + shorts.jsonl + ...), dedup by id
    seen, videos = set(), []
    for path in sorted(EXPORT_DIR.glob("*.jsonl")):
        for line in open(path):
            if not line.strip():
                continue
            v = json.loads(line)
            if v.get("id") and v["id"] not in seen:
                seen.add(v["id"]); videos.append(v)
    conn = connect()
    cur = conn.cursor()

    # platform must exist (FK)
    cur.execute("merge into platforms p using (select 'youtube' id from dual) s "
                "on (p.platform_id=s.id) when not matched then "
                "insert (platform_id, display_name) values ('youtube','YouTube')")
    # clean reload of YouTube content
    cur.execute("delete from posts where platform_id='youtube'")

    for v in videos:
        # the id names a file on disk — accept only the 11-char YouTube shape, so a
        # tampered jsonl can never write outside sources/youtube/
        if not re.fullmatch(r"[\w-]{11}", v["id"]):
            print(f"  skipping malformed video id: {v['id']!r}")
            continue
        title = v.get("title") or ""
        desc = v.get("description") or ""
        # 1) canonical Markdown
        (SRC / f"{v['id']}.md").write_text(frontmatter(v) + f"# {title}\n\n{desc}\n")
        # 2) Oracle row, with the embedding generated INSIDE the database
        emb_text = (title + ". " + desc)[:3000]
        dur = v.get("duration") or 0
        kind = "short" if 0 < dur <= 65 else "video"   # Shorts are <=60s
        cur.execute(
            """
            insert into posts (platform_id, kind, title, caption, url, published_at,
                               views, content_embedding)
            values ('youtube', :kind, :title, :caption, :url, :pub, :views,
                    vector_embedding(MINILM using :emb as data))
            """,
            kind=kind, title=title, caption=desc, url=v.get("webpage_url"),
            pub=yyyymmdd(v.get("upload_date")), views=v.get("view_count") or 0,
            emb=emb_text,
        )
    conn.commit()
    cur.execute("select count(*) from posts where platform_id='youtube'")
    print(f"loaded {cur.fetchone()[0]} YouTube videos -> sources/youtube/ + Oracle posts")
    conn.close()


if __name__ == "__main__":
    main()
