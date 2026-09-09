"""Simple CLI chat with the soccer agent. Useful for demos without a browser."""

from __future__ import annotations

import sys
import uuid

from soccer_agent.agent.loop import run_turn


def main() -> int:
    session_id = f"cli-{uuid.uuid4()}"
    print(f"Session: {session_id}  (Ctrl-D or 'exit' to quit)")
    while True:
        try:
            line = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if not line:
            continue
        if line.lower() in {"exit", "quit"}:
            return 0
        reply = run_turn(session_id, line)
        print(f"agent> {reply.text}")
        if reply.tool_trace:
            print(f"       (used {len(reply.tool_trace)} tool calls)")


if __name__ == "__main__":
    sys.exit(main())
