"""Demo the Karpathy wiki layer + its Oracle Duality / relational showcase.

  cd oracle/agent && ../../.venv/bin/python demo_wiki.py

Shows the same page three ways: as a JSON document (Duality view, with citations nested),
and the cross-link graph (relational) — all from the one Oracle database.
"""
import db


def main():
    c = db.connect()
    cur = c.cursor()
    cur.execute("SELECT page_id, topic FROM wiki_pages ORDER BY topic")
    pages = cur.fetchall()
    print(f"=== {len(pages)} compiled wiki pages ===")
    for pid, t in pages:
        print(f"  {pid}: {t}")
    if not pages:
        c.close()
        return

    pid = pages[0][0]
    print("\n=== that page as a JSON DOCUMENT via the Duality view (page + nested citations) ===")
    cur.execute("SELECT JSON_SERIALIZE(data RETURNING CLOB PRETTY) FROM wiki_page_dv "
                "WHERE JSON_VALUE(data, '$._id' RETURNING NUMBER) = :p", p=pid)
    print((cur.fetchone()[0] or "")[:1600])

    print("\n=== RELATIONAL: the cross-link graph (page -> page) ===")
    cur.execute("SELECT a.topic, b.topic FROM page_links l "
                "JOIN wiki_pages a ON a.page_id = l.from_page_id "
                "JOIN wiki_pages b ON b.page_id = l.to_page_id ORDER BY a.topic")
    for f, t in cur.fetchall()[:18]:
        print(f"  {f}  ->  {t}")

    print("\n=== RELATIONAL: which pages cite a given video? (e.g. LLM inference) ===")
    cur.execute("SELECT w.topic FROM page_sources ps JOIN wiki_pages w ON w.page_id = ps.page_id "
                "JOIN posts p ON p.post_id = ps.post_id WHERE p.title LIKE '%LLM Inference%'")
    for (topic,) in cur.fetchall():
        print(f"  cited by page: {topic}")
    c.close()


if __name__ == "__main__":
    main()
