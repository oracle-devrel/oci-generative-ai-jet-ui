"""Weekly digest agent — what the brain did last week, readable with Monday coffee.

  cd oracle/agent && ../../.venv/bin/python digest_agent.py

Agent #3 in the tutorial's roster (research answers, idea proposes, digest reports).
Collects: what you published in the last 7 days, which wiki pages changed, how big the
memory got, and what your agents worked on — then writes one tight note and SAVES IT TO
THE BRAIN, so it's on your phone via the connector. Schedule it weekly next to your sync.

The recall -> act -> record pattern in its simplest useful form: pure SQL collection,
one LLM synthesis, one write back into the shared brain.
"""
import datetime

import content
import db
import llm
import oamp_memory

SCHEMA = {"type": "object", "additionalProperties": False,
          "properties": {"digest": {"type": "string"}}, "required": ["digest"]}

SYS = ("You write a personal Monday digest for a creator about their own second-brain "
       "system. Warm but tight: short sections, bullets, no filler. Sections: WHAT YOU "
       "PUBLISHED, WHAT THE WIKI LEARNED, WHAT YOUR AGENTS DID, ONE SUGGESTION (a concrete "
       "idea grounded in the week's activity). Under 250 words.")


def collect(conn):
    cur = conn.cursor()
    cur.execute("""SELECT platform_id, title FROM posts
                   WHERE published_at >= SYSTIMESTAMP - INTERVAL '7' DAY
                     AND NVL(visibility,'content')='content'
                   ORDER BY published_at DESC FETCH FIRST 20 ROWS ONLY""")
    published = [f"[{p}] {t}" for p, t in cur.fetchall()]
    cur.execute("""SELECT topic, TO_CHAR(updated_at,'MM-DD') FROM wiki_pages
                   WHERE updated_at >= SYSTIMESTAMP - INTERVAL '7' DAY
                   ORDER BY updated_at DESC""")
    wiki = [f"{t} (refreshed {d})" for t, d in cur.fetchall()]
    cur.execute("SELECT COUNT(*) FROM posts WHERE NVL(visibility,'content')='content'")
    total = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM semantic_memory WHERE source='consolidation'")
    facts = cur.fetchone()[0]
    cur.execute("""SELECT run_id, task FROM agent_memory
                   WHERE created_at >= SYSTIMESTAMP - INTERVAL '7' DAY
                     AND NVL(visibility,'content')='content'
                   ORDER BY created_at DESC FETCH FIRST 12 ROWS ONLY""")
    runs = [f"[{r}] {t}" for r, t in cur.fetchall()]
    return published, wiki, total, facts, runs


def save_note(conn, title, text):
    # the digest synthesizes from many sources, so it gets the same write-time deny-list
    # check as memory: a body that trips it is stored quarantined, out of every read path
    vis = "business" if oamp_memory.violates_privacy(f"{title}\n{text}") else "content"
    with conn.cursor() as cur:
        cur.execute("alter session disable parallel dml")
        outid = cur.var(int)
        cur.execute("INSERT INTO posts (platform_id, kind, title, caption, visibility, "
                    "content_embedding) "
                    "VALUES ('note','note', :t, :c, :v, VECTOR_EMBEDDING(MINILM USING :e AS DATA)) "
                    "RETURNING post_id INTO :outid",
                    t=title[:1000], c=text[:8000], v=vis, e=f"{title}. {text}"[:3000], outid=outid)
        pid = int(outid.getvalue()[0])
        for i, para in enumerate(content.note_chunks(text)):
            cur.execute("INSERT INTO content_chunks (post_id, seq, chunk, embedding) "
                        "VALUES (:p, :s, :c, VECTOR_EMBEDDING(MINILM USING :e AS DATA))",
                        p=pid, s=i, c=para, e=para)
    conn.commit()


def main():
    conn = db.connect()
    try:
        published, wiki, total, facts, runs = collect(conn)
        prompt = (
            "PUBLISHED THIS WEEK:\n" + ("\n".join(f"- {p}" for p in published) or "- nothing new") +
            "\n\nWIKI PAGES THAT CHANGED:\n" + ("\n".join(f"- {w}" for w in wiki) or "- none") +
            f"\n\nBRAIN SIZE: {total} content items · {facts} consolidated facts" +
            "\n\nAGENT RUNS THIS WEEK:\n" + ("\n".join(f"- {r}" for r in runs) or "- none") +
            "\n\nWrite the digest.")
        out = llm.structured(SYS, prompt, SCHEMA, max_tokens=2000)
        today = datetime.date.today().isoformat()
        save_note(conn, f"Weekly digest {today}", out["digest"])
        print(f"=== Weekly digest {today} (saved to brain) ===\n")
        print(out["digest"])
    finally:
        conn.close()


if __name__ == "__main__":
    main()
