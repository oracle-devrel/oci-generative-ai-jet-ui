"""End-to-end demo of the whole brain in one flow: content + wiki + memory + web.

Shows (1) a grounded answer that draws on the synthesized WIKI page, raw CONTENT, and the live
WEB — citing each — then (2) a follow-up that builds on the agent's MEMORY of the first turn
(conversational + episodic): the self-improving loop. This is the spine of the blog/video demo.

  cd oracle/agent && ../../.venv/bin/python demo_brain.py
"""
import anthropic

import db
from content import list_topics
from research_agent import run_research
from conversation import new_session, record_turn, recent_turns
from memory import recall


def _stat(conn, sql):
    with conn.cursor() as c:
        return c.execute(sql).fetchone()[0]


def main():
    client = anthropic.Anthropic()
    conn = db.connect()

    print("=== the brain (one Oracle database) ===")
    print("  content items :", _stat(conn, "SELECT COUNT(*) FROM posts"))
    print("  content chunks:", _stat(conn, "SELECT COUNT(*) FROM content_chunks"))
    print("  wiki topics   :", len(list_topics(conn)))
    print("  semantic facts:", _stat(conn, "SELECT COUNT(*) FROM semantic_memory"))
    print("  past research :", _stat(conn, "SELECT COUNT(*) FROM agent_memory"))

    sid = new_session()
    q1 = ("Give me a synthesized overview of what I've covered on AI inference, "
          "and what's new on the topic this week.")
    print(f"\n=== Q1 (content + wiki + web): {q1}\n")
    a1, src1 = run_research(client, conn, q1)
    record_turn(conn, sid, "user", q1)
    record_turn(conn, sid, "assistant", a1)
    print(a1[:1100])
    print("\nsources used:", ", ".join(src1[:8]) or "(none)")

    q2 = "Of those, which should I make my next video on, and why?"
    print(f"\n=== Q2 (follow-up — uses conversational + episodic memory): {q2}\n")
    a2, _ = run_research(client, conn, q2, history=recent_turns(conn, sid))
    print(a2[:1000])

    print("\n=== what the agent recorded to memory (episodic, for next time) ===")
    for m in recall(conn, "AI inference video to make next", k=3):
        print("  -", (m.get("detail") or "")[:130])

    conn.close()


if __name__ == "__main__":
    main()
