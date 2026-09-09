"""Collect step (ChatGPT chats): your OpenAI data export -> the brain.

Reads exports/chatgpt/conversations-*.json (the ChatGPT "Export data" archive). Each conversation
becomes a post (title + your questions as the overview) plus passage chunks of the full thread.

PRIVACY: local only + gitignored export. Secrets (API keys/tokens) are redacted on the way in.
Financial/deal chats are separated afterward — run scripts/classify_private.py --apply once loaded,
so business material stays OUT of the content brain (same guard as every other source).

Run from repo root:  ./.venv/bin/python scripts/chatgpt.py
"""
import datetime
import glob
import json
import pathlib
import sys

import oracledb

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "oracle" / "agent"))
import db  # noqa: E402  (loads .env + connects to the configured DB, wallet-aware)

oracledb.defaults.fetch_lobs = False
EXPORT_DIR = ROOT / "exports" / "chatgpt"

# redact obvious credentials before anything hits the database (shared list, all loaders)
from redaction import redact  # noqa: E402


def ts(epoch):
    try:
        return datetime.datetime.utcfromtimestamp(float(epoch)) if epoch else None
    except Exception:
        return None


def messages(convo):
    """Ordered (role, text) turns from the mapping — user + assistant text only, redacted."""
    nodes = []
    for node in (convo.get("mapping") or {}).values():
        m = node.get("message")
        if not m:
            continue
        role = (m.get("author") or {}).get("role")
        if role not in ("user", "assistant"):
            continue
        content = m.get("content") or {}
        if content.get("content_type") != "text":
            continue
        parts = [p for p in (content.get("parts") or []) if isinstance(p, str) and p.strip()]
        if not parts:
            continue
        nodes.append((m.get("create_time") or 0, role, redact("\n".join(parts))))
    nodes.sort(key=lambda x: x[0])
    return [(role, text) for _, role, text in nodes]


def chunks_of(turns, size=1500):
    out, buf = [], ""
    for role, t in turns:
        piece = f"{'You' if role == 'user' else 'ChatGPT'}: {t}"
        if buf and len(buf) + len(piece) + 1 > size:
            out.append(buf)
            buf = piece
        else:
            buf = f"{buf}\n{piece}" if buf else piece
    if buf:
        out.append(buf)
    return out


def main():
    files = sorted(glob.glob(str(EXPORT_DIR / "conversations-*.json"))) or \
        [str(EXPORT_DIR / "conversations.json")]
    files = [f for f in files if pathlib.Path(f).exists()]
    if not files:
        raise SystemExit(f"no ChatGPT export found in {EXPORT_DIR}/. Request your data export "
                         "in ChatGPT (Settings -> Data controls), then unzip it there — or just "
                         "drop the zip in ~/Downloads and run scripts/sync.py "
                         "(see docs/EXPORT_GUIDE.md).")
    conn = db.connect()
    cur = conn.cursor()
    cur.execute("alter session disable parallel dml")   # Autonomous DB: allow delete+insert in one txn
    cur.execute("merge into platforms p using (select 'chatgpt' id from dual) s "
                "on (p.platform_id=s.id) when not matched then "
                "insert (platform_id, display_name) values ('chatgpt','ChatGPT chats')")
    cur.execute("delete from posts where platform_id='chatgpt'")
    # NO commit here: delete + reload is ONE transaction, so a mid-run failure
    # leaves the previous ChatGPT content intact (and readers never see a gap).
    n, total_chunks, skipped = 0, 0, 0
    for f in files:
        for c in json.load(open(f)):
            title = (c.get("title") or "").strip() or "(untitled chat)"
            turns = messages(c)
            if not turns:
                skipped += 1
                continue
            # overview = your questions (high signal, less sensitive), like the Claude loader
            asks = "\n".join(t for r, t in turns if r == "user")[:1500] or title
            emb = (title + ". " + asks)[:3000]
            outid = cur.var(oracledb.NUMBER)
            cur.execute(
                """insert into posts (platform_id, kind, title, caption, url, published_at,
                       visibility, content_embedding)
                   values ('chatgpt', 'chat', :title, :caption, null, :pub, 'content',
                       vector_embedding(MINILM using :emb as data))
                   returning post_id into :outid""",
                title=redact(title)[:1000], caption=asks, pub=ts(c.get("create_time")),
                emb=emb, outid=outid,
            )
            post_id = int(outid.getvalue()[0])
            # the FULL thread, chunked into passages (what makes chats findable)
            for i, ch in enumerate(chunks_of(turns)):
                ch = redact(ch)
                cur.execute(
                    """insert into content_chunks (post_id, seq, chunk, embedding)
                       values (:pid, :seq, :chunk, vector_embedding(MINILM using :emb as data))""",
                    pid=post_id, seq=i, chunk=ch, emb=ch[:3000],
                )
                total_chunks += 1
            n += 1
            if n % 100 == 0:
                print(f"  {n} conversations, {total_chunks} chunks...")
    conn.commit()
    print(f"loaded {n} ChatGPT conversations ({skipped} empty skipped). "
          f"Next: scripts/classify_private.py --apply")
    conn.close()


if __name__ == "__main__":
    main()
