"""Source freshness check — how long since each source last got new data?

  ./.venv/bin/python scripts/freshness.py [--no-save]

Two kinds of staleness, per source:
  export/manual sources: days since the NEWEST ITEM — past the threshold means it's
    time to request a fresh export (chat platforms have no push API).
  auto sources: days since the loader LAST TOUCHED the rows (ORA_ROWSCN) — if the
    scheduled sync stops running, this is the alarm.

No LLM: deterministic SQL + formatting. The report is saved into the brain (unless
--no-save), so "how fresh are my sources?" is answerable from any connected chat.
Schedule it weekly next to your sync job.

ADAPT THE RULES to your sources: platform key -> (mode, threshold_days, what-to-do).
"""
import datetime
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "oracle" / "agent"))
import content  # noqa: E402
import db       # noqa: E402

# EDIT ME: your sources. mode 'export'/'manual' ages by newest item; 'auto' by loader touch.
RULES = {
    "chatgpt":     ("export", 30, "request a ChatGPT export (Settings > Data controls); the watcher does the rest"),
    "claude":      ("export", 30, "request a Claude export (Settings > Privacy); the watcher does the rest"),
    "instagram":   ("auto",    3, "daily sync may not be running - check the sync log / API token"),
    "linkedin":    ("auto",    9, "weekly Apify self-scrape may not be running - check sync log / Apify credit"),
    "youtube":     ("auto",    3, "daily sync may not be running - check the sync log"),
    "notion":      ("auto",    3, "daily sync may not be running - check the sync log"),
    "claude_code": ("auto",    3, "daily sync may not be running - check the sync log"),
}
INFO_ONLY = {"note", "chat_capture"}   # written on demand; never "stale"


def _days(ts):
    return None if ts is None else max(0, (datetime.datetime.now() - ts).days)


def collect(conn):
    cur = conn.cursor()
    cur.execute("""SELECT platform_id, COUNT(*), MAX(published_at), MAX(ORA_ROWSCN)
                   FROM posts GROUP BY platform_id""")
    out = {}
    for p, n, newest, scn in cur.fetchall():
        touched = None
        if scn is not None:
            try:
                cur.execute("SELECT SCN_TO_TIMESTAMP(:s) FROM dual", s=int(scn))
                t = cur.fetchone()[0]
                touched = t.replace(tzinfo=None) if t.tzinfo else t
            except Exception:
                touched = None   # SCN older than undo retention -> not touched recently
        out[p] = {"count": n, "newest_days": _days(newest), "touched_days": _days(touched)}
    return out


def report(stats):
    today = datetime.date.today().isoformat()
    intro = ("How fresh is each data source in my second brain - when did I last export "
             f"my chats and when did each source last update? Report for {today}:")
    lines, alerts = [intro, ""], []
    for p, (mode, limit, action) in RULES.items():
        s = stats.get(p)
        if not s:
            lines.append(f"[--] {p}: no data yet")
            continue
        age = s["newest_days"] if mode in ("export", "manual") else s["touched_days"]
        stale = age is None or age > limit
        basis = "newest item" if mode in ("export", "manual") else "last loaded"
        shown = "?" if age is None else f"{age}d"
        lines.append(f"[{'!!' if stale else 'ok'}] {p}: {basis} {shown} ago "
                     f"({s['count']} items, {mode}, limit {limit}d)")
        if stale:
            alerts.append(f"- {p}: {action}")
    for p in sorted(INFO_ONLY & set(stats)):
        lines.append(f"[ok] {p}: {stats[p]['count']} items (written on demand)")
    lines.append("")
    lines.append("ACTION NEEDED:\n" + "\n".join(alerts) if alerts
                 else "ACTION NEEDED: nothing - all sources within their windows.")
    return "\n".join(lines)


def save_note(conn, title, text):
    with conn.cursor() as cur:
        cur.execute("alter session disable parallel dml")
        cur.execute("MERGE INTO platforms p USING (SELECT 'note' id FROM dual) s "
                    "ON (p.platform_id=s.id) WHEN NOT MATCHED THEN "
                    "INSERT (platform_id, display_name) VALUES ('note','Quick notes')")
        outid = cur.var(int)
        cur.execute("INSERT INTO posts (platform_id, kind, title, caption, content_embedding) "
                    "VALUES ('note','note', :t, :c, VECTOR_EMBEDDING(MINILM USING :e AS DATA)) "
                    "RETURNING post_id INTO :outid",
                    t=title[:1000], c=text[:8000], e=f"{title}. {text}"[:3000], outid=outid)
        pid = int(outid.getvalue()[0])
        for i, para in enumerate(content.note_chunks(text)):
            cur.execute("INSERT INTO content_chunks (post_id, seq, chunk, embedding) "
                        "VALUES (:p, :s, :c, VECTOR_EMBEDDING(MINILM USING :e AS DATA))",
                        p=pid, s=i, c=para, e=para)
    conn.commit()


def main():
    conn = db.connect()
    try:
        body = report(collect(conn))
        print(body)
        if "--no-save" not in sys.argv:
            save_note(conn, f"Source freshness {datetime.date.today().isoformat()}", body)
            print("\n(saved to the brain)")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
