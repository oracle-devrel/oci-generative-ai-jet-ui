"""Before/after: does memory actually help?

Shows the SAME referential follow-up answered WITHOUT conversational memory vs WITH it —
the clearest way to *see* working memory mattering. Also shows procedural memory ranking
the agent's tools by relevance to a query.

  cd oracle/agent && ../../.venv/bin/python demo_memory_effect.py
"""
import anthropic

from db import connect
from research_agent import run_research
from conversation import new_session, record_turn, recent_turns
from procedural import select_tools

FIRST = "What have I made about cloud certifications? List the specific videos."
FOLLOWUP = "Of the ones you just listed, which would make the best follow-up video, and why?"


def show(label, text):
    print(f"\n--- {label} ---\n{text[:700]}")


def main():
    client = anthropic.Anthropic()
    conn = connect()
    try:
        # Turn 1 establishes context in a session
        sid = new_session()
        a1, _ = run_research(client, conn, FIRST, history=[])
        record_turn(conn, sid, "user", FIRST)
        record_turn(conn, sid, "assistant", a1)
        print("TURN 1:", FIRST)
        print(a1[:400], "...")

        print("\n" + "=" * 72)
        print("SAME FOLLOW-UP, two ways:", FOLLOWUP)
        show("WITHOUT conversational memory (no prior turns)",
             run_research(client, conn, FOLLOWUP, history=None)[0])
        show("WITH conversational memory (prior turns loaded)",
             run_research(client, conn, FOLLOWUP, history=recent_turns(conn, sid, 12))[0])

        print("\n" + "=" * 72)
        print("PROCEDURAL memory — tools ranked by relevance to the query:")
        for q in ["find my old videos about AWS", "what's the latest 2026 AI news"]:
            picks = select_tools(conn, q, k=3)
            print(f"  '{q}'  ->  " + ", ".join(f"{p['name']}({p['dist']:.2f})" for p in picks))
    finally:
        conn.close()


if __name__ == "__main__":
    main()
