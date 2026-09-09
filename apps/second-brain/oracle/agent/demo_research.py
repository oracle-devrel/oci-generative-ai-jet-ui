"""Demo: ask the research agent questions about YOUR content.

Needs ANTHROPIC_API_KEY (in oracle/.env). The DB + content are already loaded.

  cd oracle/agent
  ../../.venv/bin/python demo_research.py
"""
from db import connect
from research_agent import run_research
import anthropic

# These work on the sample data and on your own content — swap in questions
# about YOUR material once you've loaded it (specific beats broad).
QUESTIONS = [
    "What do I have about protecting data or security?",
    "Give me an overview of the main topics in my content, with citations.",
    # needs BOTH stored content AND the web (current info):
    "Pick one topic from my content and tell me what's new in 2026 that I "
    "could follow up on.",
]


def main():
    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY
    conn = connect()
    try:
        for q in QUESTIONS:
            print("\n" + "=" * 70)
            print("Q:", q)
            answer, sources = run_research(client, conn, q)
            print("\nANSWER:\n" + answer)
            print("\nGROUNDED IN YOUR CONTENT:")
            for t in sources:
                print("  -", t)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
