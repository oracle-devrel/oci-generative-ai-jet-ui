"""THE MONEY SHOT: run the same task twice and watch run #2 beat run #1 —
because the agent recalled what worked from its Oracle-backed memory.

Usage:
    cd oracle/agent
    pip install -r requirements.txt
    export ANTHROPIC_API_KEY=...        # plus DB vars (see oracle/.env)
    python demo_same_task_twice.py
"""
import uuid
import anthropic

from db import connect
from agent import run_task
from memory import tool_stats

TOPIC = "why most creators burn out in year one"


def main():
    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env
    conn = connect()
    try:
        print("\n=== RUN 1 (no memory yet) ===")
        s1 = run_task(client, conn, run_id=f"run-{uuid.uuid4().hex[:8]}", topic=TOPIC)

        print("\n=== RUN 2 (same task — now with memory of run 1) ===")
        s2 = run_task(client, conn, run_id=f"run-{uuid.uuid4().hex[:8]}", topic=TOPIC)

        print("\n=== RESULT ===")
        print(f"  run 1 score: {s1}")
        print(f"  run 2 score: {s2}")
        print("  ✅ the agent improved" if (s2 or 0) > (s1 or 0)
              else "  (no improvement this time — run again to accumulate memory)")

        print("\n=== THE AUDITABLE FLEX (plain SQL over agent memory) ===")
        for r in tool_stats(conn):
            print(f"  {r['tool']}: {r['successes']}/{r['attempts']} "
                  f"success_rate={r['success_rate']}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
