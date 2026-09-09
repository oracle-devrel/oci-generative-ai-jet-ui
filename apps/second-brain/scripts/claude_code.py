"""Collect step (Claude Code): your local session transcripts -> the brain.

PRIVACY/SECURITY (best practice): your Claude Code transcripts can contain secrets (they
include tool output + system notes from your sessions). So this loader:
  1. ingests ONLY your user/assistant `text` (skips tool_result / tool_use / system) — that's
     where key dumps live, so skipping them removes most risk;
  2. REDACTS known secret shapes (sk-ant-, ntn_, secret_, AWS, GitHub, ...) -> [REDACTED];
  3. is LOCAL only (reads ~/.claude/projects, loads into local Oracle).
Still: rotate any keys that were ever in your sessions — that's the real safety net.

Run from repo root:  ./.venv/bin/python scripts/claude_code.py
"""
import json
import os
import pathlib

import oracledb
from dotenv import load_dotenv

ROOT = pathlib.Path(__file__).resolve().parents[1]
load_dotenv(ROOT / "oracle" / ".env")
oracledb.defaults.fetch_lobs = False
PROJECTS = pathlib.Path.home() / ".claude" / "projects"

# one shared list for every loader (scripts/redaction.py)
from redaction import redact  # noqa: E402


def connect():
    # single source of truth: env-driven, wallet-aware, NO password fallback (oracle/agent/db.py)
    import sys
    sys.path.insert(0, str(ROOT / "oracle" / "agent"))
    import db
    return db.connect()


def messages_of(path):
    """Extract (role, redacted_text) for user/assistant text only — skip tool/system blocks."""
    out = []
    for ln in open(path):
        try:
            d = json.loads(ln)
        except Exception:
            continue
        m = d.get("message")
        if not isinstance(m, dict) or m.get("role") not in ("user", "assistant"):
            continue
        c = m.get("content")
        if isinstance(c, str):
            text = c
        elif isinstance(c, list):
            text = " ".join(b.get("text", "") for b in c
                            if isinstance(b, dict) and b.get("type") == "text")
        else:
            text = ""
        text = redact(text.strip())
        if text:
            out.append((m["role"], text))
    return out


def chunks_of(msgs, size=1500):
    out, buf = [], ""
    for role, text in msgs:
        piece = f"{role}: {text}"
        if buf and len(buf) + len(piece) + 1 > size:
            out.append(buf)
            buf = piece
        else:
            buf = f"{buf}\n{piece}" if buf else piece
    if buf:
        out.append(buf)
    return out


def main():
    if not PROJECTS.exists():
        print("no ~/.claude/projects found")
        return
    conn = connect()
    cur = conn.cursor()
    cur.execute("alter session disable parallel dml")   # Autonomous: delete+insert in one txn
    cur.execute("merge into platforms p using (select 'claude_code' id from dual) s "
                "on (p.platform_id=s.id) when not matched then "
                "insert (platform_id, display_name) values ('claude_code','Claude Code sessions')")
    cur.execute("delete from posts where platform_id='claude_code'")
    n, total_chunks = 0, 0
    for f in sorted(PROJECTS.glob("*/*.jsonl")):
        msgs = messages_of(f)
        if not msgs:
            continue
        first_user = next((t for r, t in msgs if r == "user"), msgs[0][1])
        title = (first_user[:120] or "Claude Code session").replace("\n", " ")
        overview = first_user[:1500]
        outid = cur.var(oracledb.NUMBER)
        cur.execute(
            """
            insert into posts (platform_id, kind, title, caption, url, published_at, content_embedding)
            values ('claude_code', 'session', :title, :caption, null, null,
                    vector_embedding(MINILM using :emb as data))
            returning post_id into :outid
            """,
            title=title, caption=overview, emb=(title + ". " + overview)[:3000], outid=outid,
        )
        post_id = int(outid.getvalue()[0])
        for i, ch in enumerate(chunks_of(msgs)):
            cur.execute(
                """insert into content_chunks (post_id, seq, chunk, embedding)
                   values (:pid, :seq, :chunk, vector_embedding(MINILM using :emb as data))""",
                pid=post_id, seq=i, chunk=ch, emb=ch[:3000],
            )
            total_chunks += 1
        n += 1
    conn.commit()
    print(f"loaded {n} Claude Code sessions + {total_chunks} (redacted) chunks into the brain")
    conn.close()


if __name__ == "__main__":
    main()
