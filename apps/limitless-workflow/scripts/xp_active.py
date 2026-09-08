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
from limitless.xp.active_session import (
    answer_active_session,
    finish_active_session,
    hint_active_session,
    start_active_session,
    status_active_session,
)


def _print(payload: dict, as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, indent=2))
        return
    for key, value in payload.items():
        print(f"{key}: {value}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Active-session wrapper for the turn-based XP backend")
    parser.add_argument("--json", action="store_true", help="Emit JSON output")
    subparsers = parser.add_subparsers(dest="command", required=True)

    def add_json(p):
        p.add_argument("--json", action="store_true", default=argparse.SUPPRESS)

    start = subparsers.add_parser("start")
    start.add_argument("--topic", required=True)
    start.add_argument("--focus", default=None)
    add_json(start)

    answer = subparsers.add_parser("answer")
    answer.add_argument("--answer", required=True)
    add_json(answer)

    add_json(subparsers.add_parser("hint"))
    add_json(subparsers.add_parser("status"))
    add_json(subparsers.add_parser("finish"))

    args = parser.parse_args(argv)
    settings = Settings()

    if args.command == "start":
        payload = start_active_session(args.topic, args.focus, settings)
    elif args.command == "answer":
        payload = answer_active_session(args.answer, settings)
    elif args.command == "hint":
        payload = hint_active_session(settings)
    elif args.command == "status":
        payload = status_active_session()
    elif args.command == "finish":
        payload = finish_active_session(settings)
    else:
        raise ValueError(args.command)

    _print(payload, args.json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
