"""Collect step (Claude chats): your exported conversations -> the brain.

BEST PRACTICE (write discipline): ingest each conversation's distilled `summary` — not the
168MB of raw transcripts. High signal, compact, and less sensitive. Falls back to your own
(human) turns when a summary is missing.

PRIVACY: local only. The export lives under exports/ (gitignored) and loads into your local
Oracle. Your chats never leave your machine and are never committed.

Run from repo root:  ./.venv/bin/python scripts/claude_chats.py
"""
import datetime
import json
import os
import pathlib

import oracledb
from dotenv import load_dotenv

from redaction import redact

ROOT = pathlib.Path(__file__).resolve().parents[1]
load_dotenv(ROOT / "oracle" / ".env")
oracledb.defaults.fetch_lobs = False
CONV = ROOT / "exports" / "claude" / "conversations.json"


def connect():
    # single source of truth: env-driven, wallet-aware, NO password fallback (oracle/agent/db.py)
    import sys
    sys.path.insert(0, str(ROOT / "oracle" / "agent"))
    import db
    return db.connect()


def iso(s):
    if not s:
        return None
    try:
        return datetime.datetime.fromisoformat(s.replace("Z", "+00:00")).replace(tzinfo=None)
    except Exception:
        return None


def text_for(c):
    """Distilled summary if present; else the human turns (the questions you asked)."""
    s = (c.get("summary") or "").strip()
    if s:
        return redact(s)
    humans = [m.get("text", "") for m in (c.get("chat_messages") or []) if m.get("sender") == "human"]
    return redact(("\n".join(humans))[:1500])


def chunks_of(c, size=1500):
    """Group the FULL conversation into ~size-char passages with speaker labels (the detail)."""
    out, buf = [], ""
    for m in (c.get("chat_messages") or []):
        t = (m.get("text") or "").strip()
        if not t:
            continue
        who = "Human" if m.get("sender") == "human" else "Assistant"
        piece = f"{who}: {redact(t)}"
        if buf and len(buf) + len(piece) + 1 > size:
            out.append(buf)
            buf = piece
        else:
            buf = f"{buf}\n{piece}" if buf else piece
    if buf:
        out.append(buf)
    return out


def main():
    if not pathlib.Path(CONV).exists():
        raise SystemExit(f"no Claude export found at {CONV}. Request your export in Claude "
                         "(Settings -> Privacy), unzip it there — or drop the zip in "
                         "~/Downloads and run scripts/sync.py (see docs/EXPORT_GUIDE.md).")
    convos = json.load(open(CONV))
    conn = connect()
    cur = conn.cursor()
    cur.execute("alter session disable parallel dml")   # Autonomous: delete+insert in one txn
    cur.execute("merge into platforms p using (select 'claude' id from dual) s "
                "on (p.platform_id=s.id) when not matched then "
                "insert (platform_id, display_name) values ('claude','Claude chats')")
    cur.execute("delete from posts where platform_id='claude'")
    n, total_chunks = 0, 0
    for c in convos:
        name = (c.get("name") or "").strip() or "(untitled chat)"
        body = text_for(c).strip()          # the SUMMARY (overview / index)
        if not body:
            continue
        emb = (name + ". " + body)[:3000]
        outid = cur.var(oracledb.NUMBER)
        cur.execute(
            """
            insert into posts (platform_id, kind, title, caption, url, published_at, content_embedding)
            values ('claude', 'chat', :title, :caption, null, :pub,
                    vector_embedding(MINILM using :emb as data))
            returning post_id into :outid
            """,
            title=redact(name)[:1000], caption=body, pub=iso(c.get("created_at")), emb=emb, outid=outid,
        )
        post_id = int(outid.getvalue()[0])
        # the FULL content, chunked into passages (the detail)
        for i, ch in enumerate(chunks_of(c)):
            cur.execute(
                """insert into content_chunks (post_id, seq, chunk, embedding)
                   values (:pid, :seq, :chunk, vector_embedding(MINILM using :emb as data))""",
                pid=post_id, seq=i, chunk=ch, emb=ch[:3000],
            )
            total_chunks += 1
        n += 1
        if n % 50 == 0:
            print(f"  {n} conversations, {total_chunks} chunks...")
    conn.commit()
    print(f"loaded {n} Claude conversations (summary) + {total_chunks} passage chunks into the brain")
    conn.close()


if __name__ == "__main__":
    main()
