"""Enrich YouTube content with TRANSCRIPTS.

yt-dlp auto-captions (exports/youtube/subs/<id>.<lang>.json3) -> parse -> chunk into
content_chunks attached to each YouTube post. The post keeps its title+description as the
overview; the transcript becomes the passage-level detail, so the agent can quote what was
actually said in a video.

Run after downloading captions:  ./.venv/bin/python scripts/youtube_transcripts.py
"""
import glob
import json
import os
import pathlib
import re

import oracledb
from dotenv import load_dotenv

ROOT = pathlib.Path(__file__).resolve().parents[1]
load_dotenv(ROOT / "oracle" / ".env")
oracledb.defaults.fetch_lobs = False
SUBS = ROOT / "exports" / "youtube" / "subs"

ID_RE = re.compile(r"(?:v=|/shorts/|youtu\.be/)([\w-]{11})")


def connect():
    # single source of truth: env-driven, wallet-aware, NO password fallback (oracle/agent/db.py)
    import sys
    sys.path.insert(0, str(ROOT / "oracle" / "agent"))
    import db
    return db.connect()


def transcript_of(path):
    d = json.load(open(path))
    parts = [s.get("utf8", "") for e in d.get("events", []) for s in (e.get("segs") or [])]
    return re.sub(r"\s+", " ", " ".join(parts)).strip()


def chunks_of(text, size=1500):
    out, buf = [], ""
    for w in text.split():
        if buf and len(buf) + len(w) + 1 > size:
            out.append(buf)
            buf = w
        else:
            buf = f"{buf} {w}" if buf else w
    if buf:
        out.append(buf)
    return out


def main():
    conn = connect()
    cur = conn.cursor()
    # map YouTube video id -> post_id
    cur.execute("SELECT post_id, url FROM posts WHERE platform_id='youtube' AND url IS NOT NULL")
    idmap = {}
    for pid, url in cur.fetchall():
        m = ID_RE.search(url or "")
        if m:
            idmap[m.group(1)] = pid
    # idempotent: drop existing YouTube transcript chunks before reloading
    cur.execute("DELETE FROM content_chunks WHERE post_id IN "
                "(SELECT post_id FROM posts WHERE platform_id='youtube')")
    # one transcript per video — prefer 'en' over 'en-orig' (avoids duplicate chunks)
    best = {}
    for f in sorted(glob.glob(str(SUBS / "*.json3"))):
        base = os.path.basename(f)
        vid = base.split(".")[0]
        lang = base[len(vid) + 1:]
        if vid not in best or (lang.startswith("en.") and not best[vid][1].startswith("en.")):
            best[vid] = (f, lang)

    n, total = 0, 0
    for vid, (f, lang) in best.items():
        pid = idmap.get(vid)
        if not pid:
            continue
        text = transcript_of(f)
        if len(text) < 40:
            continue
        for i, ch in enumerate(chunks_of(text)):
            cur.execute(
                """INSERT INTO content_chunks (post_id, seq, chunk, embedding)
                   VALUES (:pid, :seq, :chunk, VECTOR_EMBEDDING(MINILM USING :emb AS DATA))""",
                pid=pid, seq=i, chunk=ch, emb=ch[:3000],
            )
            total += 1
        n += 1
        if n % 20 == 0:
            print(f"  {n} transcripts, {total} chunks...")
    conn.commit()
    print(f"loaded transcripts for {n} videos + {total} chunks into the brain")
    conn.close()


if __name__ == "__main__":
    main()
