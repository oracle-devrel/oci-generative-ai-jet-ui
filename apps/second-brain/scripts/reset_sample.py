"""Wipe the sample content (and everything derived from it) for a clean start.

Run this ONCE before loading your own sources, so the sample-channel videos
don't linger in your real brain:

  ./.venv/bin/python scripts/reset_sample.py

Deletes: posts, chunks, media, analytics, the compiled wiki, and the agent
memory built while you played with the sample. Keeps: the schema, the loaded
embedding model, platform lookups, and procedural (tool) memory.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "oracle" / "agent"))
import db  # noqa: E402

# children first, parents last
TABLES = [
    "page_sources",
    "page_links",
    "wiki_pages",
    "content_chunks",
    "analytics",
    "media",
    "posts",
    "agent_memory",
    "semantic_memory",
    "conversations",
]


def main():
    conn = db.connect()
    cur = conn.cursor()
    for t in TABLES:
        try:
            cur.execute(f"DELETE FROM {t}")
            print(f"  {t}: {cur.rowcount} rows deleted")
        except Exception as e:  # table may not exist in older schemas
            print(f"  {t}: skipped ({e})")
    # reset (never delete) the wiki high-water mark — MERGE also heals a missing seed row
    try:
        cur.execute(
            "MERGE INTO wiki_meta m USING (SELECT 1 id FROM dual) s ON (m.id = s.id) "
            "WHEN MATCHED THEN UPDATE SET m.last_max_post_id = 0, m.refreshed_at = SYSTIMESTAMP "
            "WHEN NOT MATCHED THEN INSERT (id, last_max_post_id, refreshed_at) "
            "VALUES (1, 0, SYSTIMESTAMP)")
        print("  wiki_meta: high-water mark reset to 0")
    except Exception as e:
        print(f"  wiki_meta: skipped ({e})")
    conn.commit()
    conn.close()
    print("Done. The brain is empty and ready for your own sources.")


if __name__ == "__main__":
    main()
