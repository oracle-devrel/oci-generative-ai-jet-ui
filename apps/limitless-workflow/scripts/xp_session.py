from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from limitless.settings import Settings
from limitless.xp.turn_engine import answer_session, finish_session, hint_session, start_session, status_session


def _print(payload: dict, as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, indent=2))
        return
    for key, value in payload.items():
        print(f"{key}: {value}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Turn-based XP Builder backend")
    parser.add_argument("--json", action="store_true", help="Emit JSON output")
    subparsers = parser.add_subparsers(dest="command", required=True)

    def add_json(p):
        p.add_argument("--json", action="store_true", default=argparse.SUPPRESS)

    start = subparsers.add_parser("start")
    start.add_argument("--topic", required=True)
    start.add_argument("--focus", default=None)
    add_json(start)

    answer = subparsers.add_parser("answer")
    answer.add_argument("--session-key", required=True)
    answer.add_argument("--answer", required=True)
    add_json(answer)

    hint = subparsers.add_parser("hint")
    hint.add_argument("--session-key", required=True)
    add_json(hint)

    status = subparsers.add_parser("status")
    status.add_argument("--session-key", required=True)
    add_json(status)

    finish = subparsers.add_parser("finish")
    finish.add_argument("--session-key", required=True)
    add_json(finish)

    args = parser.parse_args(argv)
    settings = Settings()

    if args.command == "start":
        payload = start_session(args.topic, args.focus, settings)
    elif args.command == "answer":
        payload = answer_session(args.session_key, args.answer, settings)
    elif args.command == "hint":
        payload = hint_session(args.session_key, settings)
    elif args.command == "status":
        payload = status_session(args.session_key)
    elif args.command == "finish":
        payload = finish_session(args.session_key, settings)
    else:
        raise ValueError(args.command)

    _print(payload, args.json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
