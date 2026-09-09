"""SKELETON LOADER — copy to scripts/<your_source>.py and adapt.

This is the ENTIRE contract for adding a new source to your brain. Everything
else in the system (search, wiki, agents, MCP) works off the posts table, so
a loader only has to get rows in idempotently. ~60 lines, mostly comments.

Conventions this skeleton follows (keep them):
  - a stable url per item        -> re-runs update instead of duplicating
  - a content-hash marker        -> unchanged items are skipped (cheap re-runs)
  - visibility                   -> 'content' is searchable; anything else is
                                    kept out of search, wiki, and memory
  - kind='reference'             -> searchable but EXCLUDED from the wiki
                                    compiler (for imported material that isn't
                                    your own work, e.g. e-books)
  - chunks for long text         -> queries land on the right passage
"""
import hashlib
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "oracle" / "agent"))
import db                                    # noqa: E402
from content import note_chunks              # noqa: E402  (doc_chunks for book-length text)

PLATFORM = "my_source"          # short id; shows up in search results
DISPLAY = "My Source"


def collect():
    """YOUR PART: yield dicts from your source (an API, a file, an export...).

    Required: title, text, uid (stable per item!). Optional: published_at
    (datetime), series, kind ('note' default, 'reference' for imported docs),
    visibility ('content' default).
    """
    yield {"title": "Example item", "text": "Body text here.", "uid": "example-1"}


def main():
    conn = db.connect()
    cur = conn.cursor()
    cur.execute("alter session disable parallel dml")
    cur.execute("merge into platforms p using (select :i id from dual) s "
                "on (p.platform_id=s.id) when not matched then "
                "insert (platform_id, display_name) values (:i, :d)",
                i=PLATFORM, d=DISPLAY)

    new = updated = unchanged = 0
    for item in collect():
        url = f"{PLATFORM}://{item['uid']}"
        marker = f"§{hashlib.sha256(item['text'].encode()).hexdigest()[:16]}§"
        cur.execute("SELECT post_id FROM posts WHERE url = :u "
                    "AND DBMS_LOB.INSTR(caption, :m) > 0", u=url, m=marker)
        if cur.fetchone():
            unchanged += 1
            continue
        cur.execute("SELECT post_id FROM posts WHERE url = :u", u=url)
        row = cur.fetchone()
        if row:
            cur.execute("DELETE FROM content_chunks WHERE post_id = :p", p=row[0])
            cur.execute("DELETE FROM posts WHERE post_id = :p", p=row[0])
            updated += 1
        else:
            new += 1
        visibility = item.get("visibility", "content")
        cur.execute(
            """INSERT INTO posts (platform_id, kind, title, caption, url, series,
                   published_at, visibility, content_embedding)
               VALUES (:pl, :k, :t, :c, :u, :s, :d, :v,
                       VECTOR_EMBEDDING(MINILM USING :e AS DATA))
               RETURNING post_id INTO :pid""",
            pl=PLATFORM, k=item.get("kind", "note"), t=item["title"][:490],
            c=f"{item['text'][:28000]}\n{marker}", u=url, s=item.get("series"),
            d=item.get("published_at"), v=visibility,
            e=(item["title"] + "\n" + item["text"])[:3500], pid=(pid := cur.var(int)))
        if visibility == "content":
            for i, ch in enumerate(note_chunks(item["text"])):
                cur.execute(
                    """INSERT INTO content_chunks (post_id, seq, chunk, embedding)
                       VALUES (:p, :s, :t, VECTOR_EMBEDDING(MINILM USING :t AS DATA))""",
                    p=pid.getvalue()[0], s=i, t=ch)
    conn.commit()
    conn.close()
    print(f"{PLATFORM}: {new} new, {updated} updated, {unchanged} unchanged")


if __name__ == "__main__":
    main()
