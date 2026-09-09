"""Backfill Instagram from a data export — captions + dates + spoken-word transcripts.

The export's video/image files aren't needed (the brain searches text). This reads reels.json +
posts.json for your CAPTIONS and dates, and enriches each reel with its auto-caption TRANSCRIPT
(the matching .srt) — so your hooks AND what you said land in the brain (content scope). Ongoing
performance metrics come from the API loader (scripts/instagram.py).

  ./.venv/bin/python scripts/instagram_export.py /path/to/extracted-export-root [--dry]
Idempotent AND API-aware: an item already loaded by the API loader (matched by timestamp or
caption) is NOT duplicated — instead its transcript (if any) is attached as passage chunks to
the existing post. New (older) items are inserted with caption + transcript, also chunked.
--dry prints what would happen without writing. Non-English auto-translations are dropped from
the transcript but the caption is still kept.
"""
import datetime
import json
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "oracle" / "agent"))
import db  # noqa: E402


def fix(s):
    """Instagram exports double-encode UTF-8 as latin-1 (emoji show as 'ð¤¯'). Undo it."""
    if not s:
        return ""
    try:
        return s.encode("latin-1").decode("utf-8")
    except (UnicodeDecodeError, UnicodeEncodeError):
        return s


def parse_srt(path):
    if not path or not os.path.exists(path):
        return ""
    out = []
    for ln in open(path, encoding="utf-8", errors="ignore").read().splitlines():
        ln = ln.strip()
        if ln and not ln.isdigit() and "-->" not in ln:
            out.append(ln)
    return " ".join(out)


def mostly_english(t):
    letters = [c for c in t if c.isalpha()]
    return bool(letters) and sum(ord(c) < 128 for c in letters) / len(letters) > 0.7


def _dig(d, *path):
    for k in path:
        d = (d or {}).get(k) if isinstance(d, dict) else None
    return d


def reels(root):
    f = root / "your_instagram_activity" / "media" / "reels.json"
    if not f.exists():
        return
    for it in json.load(open(f)).get("ig_reels_media", []):
        m = (it.get("media") or [{}])[0]
        yield {
            "caption": fix(m.get("title") or it.get("title") or ""),
            "ts": m.get("creation_timestamp") or it.get("creation_timestamp"),
            "sub": _dig(m, "media_metadata", "video_metadata", "subtitles", "uri"),
            "uri": m.get("uri", ""), "kind": "reel",
        }


def photo_posts(root):
    f = root / "your_instagram_activity" / "media" / "posts.json"
    if not f.exists():
        return
    for it in json.load(open(f)):
        media = it.get("media") or []
        if not media:  # caption-only posts nest media under label_values
            for lv in it.get("label_values", []):
                if lv.get("media"):
                    media = lv["media"]
                    break
        m = (media or [{}])[0]
        yield {
            "caption": fix(m.get("title") or ""),
            "ts": it.get("timestamp") or m.get("creation_timestamp"),
            "sub": None, "uri": m.get("uri", ""), "kind": "post",
        }


def _chunks_of(text, size=1500):
    out, buf = [], ""
    for para in text.split(". "):
        if buf and len(buf) + len(para) + 2 > size:
            out.append(buf)
            buf = para
        else:
            buf = f"{buf}. {para}" if buf else para
    if buf:
        out.append(buf)
    return out


def _norm_cap(c):
    return " ".join((c or "").lower().split())[:60]


def main():
    args = [a for a in sys.argv[1:] if a != "--dry"]
    dry = "--dry" in sys.argv
    if not args:
        sys.exit("usage: instagram_export.py /path/to/extracted-export-root [--dry]")
    root = pathlib.Path(args[0])
    conn = db.connect()
    cur = conn.cursor()
    cur.execute("alter session disable parallel dml")
    cur.execute("merge into platforms p using (select 'instagram' id from dual) s "
                "on (p.platform_id=s.id) when not matched then "
                "insert (platform_id, display_name) values ('instagram','Instagram')")

    # existing Instagram rows (any loader): match by minute-rounded timestamp OR caption prefix,
    # so the API year is MERGED (transcripts attached), never duplicated.
    by_minute, by_cap = {}, {}
    cur.execute("select post_id, published_at, caption from posts where platform_id='instagram'")
    oracledb_rows = cur.fetchall()
    for pid, pub, cap in oracledb_rows:
        if pub:
            epoch_min = int(pub.replace(tzinfo=datetime.timezone.utc).timestamp() // 60)
            by_minute[epoch_min] = pid
        key = _norm_cap(cap if isinstance(cap, str) else (cap.read() if cap else ""))
        if len(key) >= 25:
            by_cap[key] = pid

    n = merged = skip = chunks = 0
    for it in list(reels(root)) + list(photo_posts(root)):
        cap = (it["caption"] or "").strip()
        # subtitle paths come from the export's own JSON — resolve and require they stay
        # inside the export root, so a tampered archive can't read arbitrary local files
        transcript = ""
        if it["sub"]:
            sub_path = (root / it["sub"]).resolve()
            if sub_path.is_relative_to(root.resolve()):
                transcript = parse_srt(str(sub_path))
            else:
                print(f"  skipping subtitle outside export root: {it['sub']!r}")
        if transcript and not mostly_english(transcript):
            transcript = ""
        body = cap + (("\n\n[transcript] " + transcript) if transcript else "")
        if len(body.strip()) < 20:
            skip += 1
            continue

        pid = None
        if it["ts"]:
            pid = by_minute.get(int(it["ts"] // 60))
        if pid is None:
            key = _norm_cap(cap)
            pid = by_cap.get(key) if len(key) >= 25 else None

        if pid is not None:
            # already in the brain (API loader) — just attach the transcript as passages
            if transcript:
                merged += 1
                if not dry:
                    cur.execute("delete from content_chunks where post_id = :p", p=pid)
                    for i, ch in enumerate(_chunks_of(transcript)):
                        cur.execute(
                            """insert into content_chunks (post_id, seq, chunk, embedding)
                               values (:pid, :seq, :chunk,
                                       vector_embedding(MINILM using :emb as data))""",
                            pid=pid, seq=i, chunk=ch, emb=ch[:3000])
                        chunks += 1
            continue

        mid = os.path.splitext(os.path.basename(it["uri"]))[0] or str(it["ts"])
        url = f"https://www.instagram.com/reel/{mid}/"
        title = (cap.split("\n", 1)[0] or transcript)[:150]
        pub = (datetime.datetime.fromtimestamp(it["ts"], tz=datetime.timezone.utc)
               .replace(tzinfo=None) if it["ts"] else None)
        n += 1
        if dry:
            continue
        cur.execute("delete from posts where url = :u", u=url)
        outid = cur.var(int)
        cur.execute(
            """insert into posts (platform_id, kind, title, caption, url, published_at,
                   visibility, content_embedding)
               values ('instagram', :k, :t, :c, :u, :p, 'content',
                   vector_embedding(MINILM using :e as data))
               returning post_id into :outid""",
            k=it["kind"], t=title, c=body[:4000], u=url, p=pub,
            e=(title + ". " + body)[:3000], outid=outid)
        new_pid = int(outid.getvalue()[0])
        if transcript:
            for i, ch in enumerate(_chunks_of(transcript)):
                cur.execute(
                    """insert into content_chunks (post_id, seq, chunk, embedding)
                       values (:pid, :seq, :chunk,
                               vector_embedding(MINILM using :emb as data))""",
                    pid=new_pid, seq=i, chunk=ch, emb=ch[:3000])
                chunks += 1

    if dry:
        print(f"DRY RUN: would insert {n} new items, attach transcripts to {merged} "
              f"existing posts, skip {skip} empty")
        conn.close()
        return
    conn.commit()
    total = cur.execute("select count(*) from posts where platform_id='instagram'").fetchone()[0]
    print(f"ingested {n} new items, merged transcripts onto {merged} existing posts "
          f"({chunks} chunks, {skip} skipped as empty); total instagram now {total}")
    conn.close()


if __name__ == "__main__":
    main()
