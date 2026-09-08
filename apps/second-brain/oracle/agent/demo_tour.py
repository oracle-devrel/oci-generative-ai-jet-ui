"""A fast, no-LLM tour of the whole brain — runs in seconds, costs nothing, shows every layer.
Good for a screen-record: stats -> search (3 levels) -> hybrid rescue -> wiki as a Duality
document -> the relational graph -> learned memory.

  cd oracle/agent && ../../.venv/bin/python demo_tour.py
"""
import db
import content


def main():
    c = db.connect()
    cur = c.cursor()

    print("=== 1. the brain (one Oracle 26ai database) ===")
    for t in ["posts", "content_chunks", "wiki_pages", "page_links", "page_sources",
              "agent_memory", "semantic_memory"]:
        print(f"   {t:16} {cur.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]:>7}")

    print("\n=== 2. semantic search — three levels at once ===")
    for r in content.search_content(c, "how does AI inference work", 6):
        print(f"   [{r['lvl']:7}] {(r['title'] or '')[:54]}")

    print("\n=== 3. hybrid (RRF) rescues an exact name pure-vector buries ===")
    q = "vector database"   # an exact term/name pure-vector can bury — swap for one in your content
    vec = {(_t(r)) for r in content.search_content(c, q, 5)}
    hyb = content.search_hybrid(c, q, 5)
    for r in hyb:
        tag = "＋" if _t(r) not in vec else " "
        print(f"   {tag} {(r['title'] or '')[:58]}")

    print("\n=== 4. a wiki page as a JSON document (Duality view) ===")
    cur.execute("SELECT JSON_SERIALIZE(data RETURNING CLOB) FROM wiki_page_dv FETCH FIRST 1 ROWS ONLY")
    import json
    doc = json.loads(cur.fetchone()[0])
    print(f"   topic: {doc['topic']}   ·   citations nested: {len(doc.get('sources', []))}")

    print("\n=== 5. relational: the wiki cross-link graph ===")
    cur.execute("SELECT a.topic, b.topic FROM page_links l "
                "JOIN wiki_pages a ON a.page_id=l.from_page_id "
                "JOIN wiki_pages b ON b.page_id=l.to_page_id FETCH FIRST 6 ROWS ONLY")
    for a, b in cur.fetchall():
        print(f"   {a[:34]:34} -> {b[:30]}")

    print("\n=== 6. what the agent has learned (semantic memory) ===")
    cur.execute("SELECT category, fact FROM semantic_memory FETCH FIRST 4 ROWS ONLY")
    for cat, fact in cur.fetchall():
        print(f"   [{cat}] {fact[:64]}")

    c.close()


def _t(r):
    return r.get("title") or ""


if __name__ == "__main__":
    main()
