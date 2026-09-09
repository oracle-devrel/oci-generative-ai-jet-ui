"""Demo: consolidate episodic memory -> semantic memory, then recall facts.

  cd oracle/agent && ../../.venv/bin/python demo_memory.py
"""
import anthropic
from db import connect
from semantic_memory import consolidate, semantic_recall


def main():
    client = anthropic.Anthropic()
    conn = connect()
    try:
        print("Consolidating episodic memory (past research runs) -> semantic facts...\n")
        facts = consolidate(client, conn)
        print(f"Learned {len(facts)} durable facts:")
        for f in facts:
            print(f"  [{f.get('category','')}] {f['fact']}")
        print("\nSemantic recall for 'advice for people new to tech':")
        for r in semantic_recall(conn, "advice for people new to tech", k=4):
            print(f"  {r['dist']:.3f}  [{r['category']}] {r['fact']}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
