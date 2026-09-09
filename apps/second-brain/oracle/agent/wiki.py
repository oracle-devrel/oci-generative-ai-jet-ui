"""Karpathy wiki compiler — turn your content into self-maintaining, linked topic pages.

An LLM (1) proposes coherent topics from your content, then (2) compiles a synthesized page
per topic, citing the posts it used and linking to related topics. Pages are embedded and
stored in Oracle (wiki_pages + page_sources + page_links).

  python wiki.py            # full (re)build: propose topics + compile every page
  python wiki.py --refresh  # SELF-IMPROVING: update touched pages + GROW new ones (cheap)

The refresh is what makes the layer self-improving, in both directions: it recompiles the
pages your new content touches, AND proposes new topic pages when new content clusters
outside every existing topic. No new content means no LLM calls at all.
"""
import json
import sys

import oracledb
import anthropic

import llm
from db import connect          # importing db loads oracle/.env (incl. the LLM config)
from content import search_content

MODEL = "claude-opus-4-8"

TOPICS_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "properties": {"topics": {"type": "array", "items": {
        "type": "object", "additionalProperties": False,
        "properties": {"topic": {"type": "string"}}, "required": ["topic"]}}},
    "required": ["topics"],
}
PAGE_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "properties": {
        "body": {"type": "string"},
        "cited_post_ids": {"type": "array", "items": {"type": "integer"}},
        "links": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["body", "cited_post_ids", "links"],
}


def _json(client, system, prompt, schema, max_tokens=2048):
    # provider-agnostic: LLM_PROVIDER in oracle/.env picks anthropic / openai / ollama
    return llm.structured(system, prompt, schema, max_tokens)


def propose_topics(client, conn, n=10):
    cur = conn.cursor()
    cur.execute("SELECT title FROM posts WHERE title IS NOT NULL "
                "AND NVL(visibility,'content') = 'content' "
                "AND platform_id IN ('youtube','notion') FETCH FIRST 200 ROWS ONLY")
    titles = [r[0] for r in cur.fetchall()]
    cur.execute("SELECT fact FROM semantic_memory FETCH FIRST 30 ROWS ONLY")
    facts = [r[0] for r in cur.fetchall()]
    prompt = (f"Propose {n} coherent TOPIC pages that group this creator's recurring themes "
              "(for a personal knowledge wiki). Return concise topic names.\n\n"
              "CONTENT TITLES:\n" + "\n".join(f"- {t}" for t in titles[:200]) +
              "\n\nLEARNED FACTS:\n" + "\n".join(f"- {f}" for f in facts))
    return [t["topic"] for t in _json(client, "You organize a creator's content into wiki topics.",
                                      prompt, TOPICS_SCHEMA, 1024)["topics"]]


def compile_page(client, conn, topic, all_topics):
    """Synthesize one page from the content most relevant to `topic`. Returns (body, cites, links)."""
    hits = search_content(conn, topic, k=12)
    valid = {h["post_id"] for h in hits if h["post_id"]}
    src = "\n".join(f"[{h['post_id']}] ({h['platform_id']}/{h['kind']}) {h['title']}: "
                    f"{(h['snippet'] or '')[:160]}" for h in hits if h["post_id"])
    others = ", ".join(t for t in all_topics if t != topic)
    prompt = (f"Compile a concise wiki page for the topic \"{topic}\", synthesizing what THIS "
              f"creator has covered/said about it — grounded ONLY in the content below. Cite the "
              f"[post_id]s you actually used (cited_post_ids). From this list, pick related topics "
              f"to link: {others}.\n\nCONTENT:\n{src}")
    d = _json(client, "You compile grounded, synthesized wiki pages from a creator's own content.",
              prompt, PAGE_SCHEMA, 2048)
    cites = [i for i in d.get("cited_post_ids", []) if i in valid]
    return d["body"], cites, d.get("links", [])


# --- storage helpers -------------------------------------------------------------------------

def _insert_page(cur, topic, body):
    outid = cur.var(oracledb.NUMBER)
    cur.execute("INSERT INTO wiki_pages (topic, body, embedding) "
                "VALUES (:t, :b, VECTOR_EMBEDDING(MINILM USING :e AS DATA)) "
                "RETURNING page_id INTO :o",
                t=topic[:200], b=body, e=f"{topic}. {body}"[:3000], o=outid)
    return int(outid.getvalue()[0])


def _update_page(cur, page_id, topic, body):
    cur.execute("UPDATE wiki_pages SET body = :b, "
                "embedding = VECTOR_EMBEDDING(MINILM USING :e AS DATA), updated_at = SYSTIMESTAMP "
                "WHERE page_id = :p", b=body, e=f"{topic}. {body}"[:3000], p=page_id)


def _set_citations(cur, page_id, cites):
    cur.execute("DELETE FROM page_sources WHERE page_id = :p", p=page_id)
    for post_id in cites:
        try:
            cur.execute("INSERT INTO page_sources (page_id, post_id) VALUES (:p, :s)",
                        p=page_id, s=int(post_id))
        except oracledb.DatabaseError:
            pass


def _set_links(cur, page_id, link_names, name2id):
    cur.execute("DELETE FROM page_links WHERE from_page_id = :p", p=page_id)
    for lk in link_names:
        tid = name2id.get((lk or "").lower())
        if tid and tid != page_id:
            try:
                cur.execute("INSERT INTO page_links (from_page_id, to_page_id) VALUES (:f, :t)",
                            f=page_id, t=tid)
            except oracledb.DatabaseError:
                pass


def _max_post_id(cur):
    cur.execute("SELECT NVL(MAX(post_id), 0) FROM posts")
    return int(cur.fetchone()[0])


def _set_hwm(cur, value):
    # MERGE, not UPDATE: survives a missing seed row (e.g. after a data reset),
    # where an UPDATE would silently touch 0 rows and freeze the high-water mark.
    cur.execute(
        "MERGE INTO wiki_meta m USING (SELECT 1 id FROM dual) s ON (m.id = s.id) "
        "WHEN MATCHED THEN UPDATE SET m.last_max_post_id = :v, m.refreshed_at = SYSTIMESTAMP "
        "WHEN NOT MATCHED THEN INSERT (id, last_max_post_id, refreshed_at) "
        "VALUES (1, :v, SYSTIMESTAMP)", v=value)


def _get_hwm(cur):
    cur.execute("SELECT last_max_post_id FROM wiki_meta WHERE id = 1")
    row = cur.fetchone()
    return int(row[0]) if row else 0


# --- build (full) and refresh (incremental) --------------------------------------------------

def build_wiki(client, conn, n=10):
    """Full rebuild in ONE transaction. Readers keep the old wiki until the new one
    commits, and any failure (LLM, network) rolls back to the old wiki intact —
    never an empty brain."""
    cur = conn.cursor()
    try:
        # Autonomous DB defaults sessions to parallel DML; the small-table MERGE in
        # _set_hwm then self-deadlocks (ORA-12801/ORA-12860). Disable it FIRST — before
        # any DML opens the transaction — since Oracle forbids changing the parallel DML
        # state once a txn is active (ORA-12841). Same guard every other write path uses.
        cur.execute("alter session disable parallel dml")
        cur.execute("DELETE FROM wiki_pages")   # cascades to links + sources
        topics = propose_topics(client, conn, n)
        name2id, link_plan = {}, {}
        for topic in topics:
            body, cites, links = compile_page(client, conn, topic, topics)
            pid = _insert_page(cur, topic, body)
            name2id[topic.lower()] = pid
            link_plan[pid] = links
            _set_citations(cur, pid, cites)
            print(f"  compiled '{topic}'  ({len(cites)} citations)")
        for pid, links in link_plan.items():
            _set_links(cur, pid, links, name2id)
        _set_hwm(cur, _max_post_id(cur))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    print(f"built {len(topics)} wiki pages")


def propose_new_topics(client, conn, existing_topics, uncovered_ids, max_new=3):
    """GROW the wiki: when new content lands that no existing topic's retrieval reaches,
    ask whether it clusters into genuinely NEW topics. Strict: returns [] unless the
    uncovered posts clearly form a coherent theme not already covered."""
    if not uncovered_ids:
        return []
    binds = {f"i{j}": v for j, v in enumerate(list(uncovered_ids)[:400])}
    inl = ",".join(f":i{j}" for j in range(len(binds)))
    with conn.cursor() as cur:
        cur.execute(f"SELECT title FROM posts WHERE post_id IN ({inl}) AND title IS NOT NULL "
                    f"FETCH FIRST 40 ROWS ONLY", **binds)
        titles = [r[0] for r in cur.fetchall()]
    if len(titles) < 8:
        return []
    prompt = ("EXISTING WIKI TOPICS:\n" + "\n".join(f"- {t}" for t in existing_topics) +
              "\n\nNEW CONTENT not reached by any existing topic:\n" +
              "\n".join(f"- {t}" for t in titles) +
              f"\n\nDo these cluster into up to {max_new} coherent NEW wiki topics that are "
              "clearly NOT covered by the existing ones? Only propose a topic when a real "
              "cluster exists — return an empty list if the new content is scattered or "
              "already covered.")
    got = _json(client, "You decide when a creator's new content deserves NEW wiki topic pages. "
                        "Be conservative — most refreshes should propose nothing.",
                prompt, TOPICS_SCHEMA, 1024)["topics"]
    return [t["topic"] for t in got][:max_new]


def refresh_wiki(client, conn):
    """SELF-IMPROVING, both directions: recompile topics whose top retrieval now includes
    posts newer than the last compile, AND propose new topic pages when new content clusters
    outside every existing topic. No new content -> no LLM calls."""
    cur = conn.cursor()
    # Disable parallel DML up front (before the first _update_page/_set_hwm write) so the
    # small-table MERGEs don't self-deadlock; must precede any DML to avoid ORA-12841.
    cur.execute("alter session disable parallel dml")
    hwm = _get_hwm(cur)
    cur_max = _max_post_id(cur)
    if cur_max <= hwm:
        print(f"no new content since last compile (max post_id {cur_max}); nothing to refresh")
        return
    new_ids = set()
    # kind='reference' (e-books, imported documents) is searchable but must never
    # reshape the wiki: the wiki synthesizes YOUR work, not your library.
    cur.execute("SELECT post_id FROM posts WHERE post_id > :h "
                "AND NVL(visibility,'content') = 'content' "
                "AND NVL(kind,'x') <> 'reference'", h=hwm)
    new_ids = {int(r[0]) for r in cur.fetchall()}
    print(f"{len(new_ids)} new posts since last compile — checking which topics they touch")

    cur.execute("SELECT page_id, topic FROM wiki_pages")
    existing = cur.fetchall()
    name2id = {t.lower(): pid for pid, t in existing}
    topics = [t for _, t in existing]
    link_plan, refreshed, skipped, covered = {}, [], [], set()
    for pid, topic in existing:
        hits = search_content(conn, topic, k=12)
        touched = {h["post_id"] for h in hits if h["post_id"]} & new_ids
        covered |= touched
        if not touched:
            skipped.append(topic)
            continue
        body, cites, links = compile_page(client, conn, topic, topics)
        _update_page(cur, pid, topic, body)
        _set_citations(cur, pid, cites)
        link_plan[pid] = links
        refreshed.append(topic)
        conn.commit()
        print(f"  refreshed '{topic}'  ({len(cites)} citations)")

    # growth: new content that NO existing topic reaches may deserve its own page(s)
    uncovered = new_ids - covered
    added = []
    if len(uncovered) >= int(__import__("os").environ.get("WIKI_NEW_TOPIC_MIN", "15")):
        for topic in propose_new_topics(client, conn, topics, uncovered):
            body, cites, links = compile_page(client, conn, topic, topics + added)
            pid = _insert_page(cur, topic, body)
            name2id[topic.lower()] = pid
            link_plan[pid] = links
            _set_citations(cur, pid, cites)
            added.append(topic)
            conn.commit()
            print(f"  NEW page '{topic}'  ({len(cites)} citations)")

    for pid, links in link_plan.items():
        _set_links(cur, pid, links, name2id)
    _set_hwm(cur, cur_max)
    conn.commit()
    print(f"refresh done: {len(refreshed)} refreshed, {len(added)} new pages, "
          f"{len(skipped)} unchanged")


def main():
    client = anthropic.Anthropic()
    conn = connect()
    try:
        if "--refresh" in sys.argv:
            refresh_wiki(client, conn)
        else:
            build_wiki(client, conn)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
