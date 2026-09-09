"""Chat with your research agent — ask anything about your content; it searches your
brain + the web, answers grounded with citations, and remembers each exchange.

  cd oracle/agent
  ../../.venv/bin/python ask.py

Type a question and press enter. Type 'exit' (or Ctrl-D) to quit.
"""
import anthropic

from db import connect
from research_agent import run_research
from conversation import new_session, record_turn, recent_turns


def main():
    client = anthropic.Anthropic()
    conn = connect()
    sid = new_session()
    print(f"🧠  Ask your brain. (type 'exit' to quit)  [session {sid}]\n")
    try:
        while True:
            try:
                q = input("you> ").strip()
            except EOFError:
                break
            if not q:
                continue
            if q.lower() in ("exit", "quit"):
                break
            history = recent_turns(conn, sid, 12)        # working memory: prior turns
            answer, sources = run_research(client, conn, q, history=history)
            record_turn(conn, sid, "user", q)            # persist the exchange
            record_turn(conn, sid, "assistant", answer)
            print("\n" + answer + "\n")
            if sources:
                print("grounded in: " + ", ".join(sources[:6]) + "\n")
    finally:
        conn.close()
        print("\nbye 👋")


if __name__ == "__main__":
    main()
